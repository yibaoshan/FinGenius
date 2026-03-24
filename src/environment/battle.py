import asyncio
import random
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict

from src.agent.base import BaseAgent
from src.agent.toolcall import ToolCallAgent
from src.schema import AgentState
from src.environment.base import BaseEnvironment
from src.logger import logger
from src.prompt.battle import (
    EVENT_TYPES,
    VOTE_OPTIONS,
    get_agent_instructions,
    get_broadcast_message,
    get_report_context,
)
from src.tool.base import BaseTool, ToolResult
from src.tool.battle import Battle
from src.tool.terminate import Terminate
from src.tool.tool_collection import ToolCollection


class BattleState(BaseModel):
    """Battle state tracking"""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    active_agents: Dict[str, str] = Field(default_factory=dict)
    agent_order: List[str] = Field(default_factory=list)  # 发言顺序
    terminated_agents: Dict[str, bool] = Field(default_factory=dict)
    battle_history: List[Dict[str, Any]] = Field(default_factory=list)
    debate_history: List[Dict[str, Any]] = Field(default_factory=list)  # 辩论历史
    
    # 新的投票机制：支持每轮投票
    round_votes: Dict[int, Dict[str, str]] = Field(default_factory=dict)  # {round: {agent_id: vote}}
    final_votes: Dict[str, str] = Field(default_factory=dict)  # 最终投票结果
    vote_results: Dict[str, int] = Field(
        default_factory=lambda: {option: 0 for option in VOTE_OPTIONS}
    )
    battle_highlights: List[Dict[str, Any]] = Field(default_factory=list)
    battle_over: bool = Field(default=False)
    current_round: int = Field(default=0)  # 当前轮次
    current_speaker_index: int = Field(default=0)  # 当前发言者索引

    def is_agent_active(self, agent_id: str) -> bool:
        """Check if agent is active and can participate"""
        return (
            agent_id in self.active_agents
            and agent_id not in self.terminated_agents
        )
    
    def can_agent_speak(self, agent_id: str) -> bool:
        """Check if agent can speak in debate (separate from voting status)"""
        return (
            agent_id in self.active_agents
            and agent_id not in self.terminated_agents
        )
    
    def can_agent_vote(self, agent_id: str) -> bool:
        """Check if agent can vote (not terminated, can vote multiple times)"""
        return (
            agent_id in self.active_agents
            and agent_id not in self.terminated_agents
        )

    def add_event(self, event_type: str, agent_id: str, **kwargs) -> Dict[str, Any]:
        """Add event to history and return the event"""
        from datetime import datetime
        
        event = {
            "type": event_type,
            "agent_id": agent_id,
            "agent_name": self.active_agents.get(agent_id, "Unknown"),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            **kwargs,
        }
        self.battle_history.append(event)
        return event

    def mark_terminated(self, agent_id: str, reason: str = "Unknown reason") -> None:
        """Mark agent as terminated"""
        self.terminated_agents[agent_id] = True

    def record_vote(self, agent_id: str, vote: str, round_num: int = None) -> None:
        """Record agent vote for current round"""
        logger.info(f"🗳️ Recording vote: {agent_id} -> {vote} (round {round_num})")
        
        # 验证投票选项
        if vote not in VOTE_OPTIONS:
            logger.error(f"❌ Invalid vote option '{vote}' from {agent_id}. Valid options: {VOTE_OPTIONS}")
            return
        
        # 记录当前轮次的投票
        if round_num is not None:
            if round_num not in self.round_votes:
                self.round_votes[round_num] = {}
            self.round_votes[round_num][agent_id] = vote
            logger.info(f"📊 Recorded {agent_id} vote for round {round_num}: {vote}")
        
        # 更新最终投票（最新的投票覆盖之前的）
        old_vote = self.final_votes.get(agent_id, "None")
        self.final_votes[agent_id] = vote
        logger.info(f"🔄 Updated final vote for {agent_id}: {old_vote} -> {vote}")
        
        # 重新计算投票统计
        self._recalculate_vote_results()
    
    def _recalculate_vote_results(self) -> None:
        """重新计算投票统计结果"""
        logger.info(f"🔄 Recalculating vote results...")
        logger.info(f"📋 Active agents: {list(self.active_agents.keys())} (total: {len(self.active_agents)})")
        logger.info(f"📋 Final votes: {self.final_votes} (total: {len(self.final_votes)})")
        logger.info(f"📋 Terminated agents: {list(self.terminated_agents.keys())} (total: {len(self.terminated_agents)})")
        
        # 重置计数
        self.vote_results = {option: 0 for option in VOTE_OPTIONS}
        
        # 基于最终投票重新计算
        for agent_id, vote in self.final_votes.items():
            if vote in self.vote_results:
                self.vote_results[vote] += 1
                logger.info(f"✅ Counted vote: {agent_id} -> {vote}")
            else:
                logger.error(f"❌ Invalid vote option '{vote}' from {agent_id}, skipping")
        
        # 检查是否有专家没有投票
        missing_votes = []
        for agent_id in self.active_agents.keys():
            if agent_id not in self.terminated_agents and agent_id not in self.final_votes:
                missing_votes.append(agent_id)
        
        if missing_votes:
            logger.warning(f"⚠️ Agents without final votes: {missing_votes}")
        
        logger.info(f"📊 Final vote results: {self.vote_results} (total votes: {sum(self.vote_results.values())})")

    def add_highlight(self, agent_name: str, content: str) -> None:
        """Add highlight if content is significant with deduplication"""
        if len(content) < 20:  # Skip short content
            return
            
        # 检查是否已存在相同的highlight（防止重复）
        content_hash = hash(content.strip())
        for existing in self.battle_highlights:
            if (existing["agent"] == agent_name and 
                hash(existing["point"].strip()) == content_hash):
                logger.debug(f"🔄 Skipping duplicate highlight from {agent_name}")
                return
        
        # 限制每个专家的highlight数量（防止刷屏）
        agent_highlights = [h for h in self.battle_highlights if h["agent"] == agent_name]
        if len(agent_highlights) >= 3:  # 每个专家最多3条highlight
            logger.warning(f"⚠️ Agent {agent_name} has reached highlight limit (3), skipping new highlight")
            return
            
        self.battle_highlights.append({"agent": agent_name, "point": content})
        logger.info(f"✅ Added highlight from {agent_name} (total: {len(self.battle_highlights)})")

    def all_agents_decided(self) -> bool:
        """Check if all agents have made their final decision (voted at least once or terminated)"""
        return all(
            agent_id in self.final_votes or agent_id in self.terminated_agents
            for agent_id in self.active_agents
        )


class BattleEnvironment(BaseEnvironment):
    """Environment for agents to battle and vote on stock sentiment"""

    name: str = Field(default="battle_environment")
    description: str = Field(default="Environment for stock market battles")
    state: BattleState = Field(default_factory=BattleState)
    tools: Dict[str, BaseTool] = Field(default_factory=dict)
    max_steps: int = Field(default=3, description="Maximum steps for each agent")
    debate_rounds: int = Field(default=2, description="Number of debate rounds")
    tool_calls: int = Field(default=0, description="Total number of tool calls")
    llm_calls: int = Field(default=0, description="Total number of LLM calls")

    async def initialize(self) -> None:
        """Initialize the battle environment"""
        await super().initialize()
        self.state = BattleState()
        logger.info(f"Battle environment initialized (max_steps={self.max_steps})")

    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent with battle tools and instructions"""
        super().register_agent(agent)
        agent_id = agent.name
        self.state.active_agents[agent_id] = agent.name
        
        # Record agent speaking order
        if agent_id not in self.state.agent_order:
            self.state.agent_order.append(agent_id)

        # Set max_steps for the agent
        if hasattr(agent, "max_steps"):
            agent.max_steps = self.max_steps

        if isinstance(agent, ToolCallAgent) and hasattr(agent, "available_tools"):
            battle_tool = Battle(agent_id=agent_id)
            battle_tool.controller = self
            self.tools[agent_id] = battle_tool
            agent.available_tools = ToolCollection(battle_tool, Terminate())

            # Add battle instructions while preserving research context
            agent_description = getattr(agent, "description", "")
            agent_instructions = get_agent_instructions(agent.name, agent_description)
            # Provider compatibility: some OpenAI-compatible gateways reject
            # requests containing multiple system messages in one completion call.
            # Use user-context message for battle instructions.
            agent.update_memory("user", f"[Battle Environment] {agent_instructions}")
            
            logger.info(f"Agent {agent_id} registered for battle with preserved research context")

    async def run(self, report: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Run the battle environment with the given research report."""
        try:
            # Reset counters
            self.tool_calls = 0
            self.llm_calls = 0
            
            # Send initial context to all agents
            await self._send_initial_context(report)
            
            # Run structured debate
            await self._run_structured_debate()
            
            # Run final voting
            await self._run_final_voting()

            # Return results
            return self._prepare_results()
            
        except Exception as e:
            logger.error(f"Battle environment execution failed: {str(e)}")
            return None

    async def handle_speak(self, agent_id: str, content: str) -> ToolResult:
        """Handle agent speech during debate."""
        self.tool_calls += 1
        if not self.state.can_agent_speak(agent_id):
            return ToolResult(error=self._get_error_message(agent_id, "speak"))

        event = self.state.add_event(EVENT_TYPES["speak"], agent_id, content=content)
        self.state.add_highlight(event["agent_name"], content)
        
        # 同时将辩论发言添加到debate_history中，用于HTML报告生成
        debate_entry = {
            "speaker": event["agent_name"],
            "content": content,
            "timestamp": event.get("timestamp", ""),
            "round": getattr(self.state, 'current_round', 0),
            "agent_id": agent_id
        }
        self.state.debate_history.append(debate_entry)
        
        await self._broadcast_message(agent_id, content, EVENT_TYPES["speak"])

        return ToolResult(output=f"Message sent: {content}")

    async def handle_vote(self, agent_id: str, vote: str) -> ToolResult:
        """Handle agent voting."""
        self.tool_calls += 1
        if not self.state.can_agent_vote(agent_id):
            return ToolResult(error=self._get_error_message(agent_id, "vote"))

        if vote not in VOTE_OPTIONS:
            return ToolResult(
                error=f"Invalid vote option. Must be one of: {', '.join(VOTE_OPTIONS)}"
            )

        # 传递当前轮次信息
        current_round = getattr(self.state, 'current_round', 0)
        self.state.record_vote(agent_id, vote, current_round)
        self.state.add_event(EVENT_TYPES["vote"], agent_id, vote=vote, round=current_round)
        await self._broadcast_message(agent_id, f"voted {vote} (Round {current_round})", EVENT_TYPES["vote"])

        return ToolResult(output=f"Vote recorded: {vote} for Round {current_round}")

    async def cleanup(self) -> None:
        """Clean up battle resources"""
        for tool in self.tools.values():
            tool.controller = None
        await super().cleanup()

    # Private helper methods
    def _get_error_message(self, agent_id: str, action: str = "participate") -> str:
        """Get appropriate error message for agent"""
        if agent_id not in self.state.active_agents:
            return f"Agent {agent_id} is not registered"
        
        if agent_id in self.state.terminated_agents:
            return f"Agent {agent_id} has been terminated and cannot {action}"
        
        return f"Agent {agent_id} cannot {action} at this time"

    async def _run_agent_steps(self) -> None:
        """Run steps for all active agents."""
        for agent_id, agent in self.agents.items():
            if not self.state.is_agent_active(agent_id):
                continue
                
            try:
                result = await agent.step()
                self.llm_calls += 1
                if isinstance(result, str) and result == AgentState.FINISHED:
                    self.state.mark_terminated(agent_id, "Agent finished")
                elif isinstance(result, BaseAgent):
                    if result.state == AgentState.FINISHED:
                        self.state.mark_terminated(agent_id, "Agent finished")
            except Exception as e:
                logger.error(f"Error running agent {agent_id} step: {str(e)}")
                self.state.mark_terminated(agent_id, str(e))

    async def _send_initial_context(self, report: Dict[str, Any]) -> None:
        """Send comprehensive research results to all agents."""
        # 构建完整的研究分析上下文
        context_parts = ["# 📊 完整研究阶段分析结果\n"]
        
        # 添加各专家的详细分析
        expert_analyses = {
            "sentiment": "🧠 市场情绪分析师",
            "risk": "🛡️ 风险控制专家", 
            "hot_money": "💰 游资分析师",
            "technical": "📈 技术分析师",
            "chip_analysis": "🔍 筹码分析师",
            "big_deal": "💹 大单分析师"
        }
        
        for analysis_key, expert_name in expert_analyses.items():
            if analysis_key in report:
                analysis_content = report[analysis_key]
                if analysis_content and str(analysis_content).strip():
                    context_parts.append(f"## {expert_name}分析结果:")
                    context_parts.append(f"{analysis_content}")
                    context_parts.append("")  # 空行分隔
        
        # 添加基本信息（如果有）
        if "basic_info" in report:
            context_parts.append("## 📋 股票基本信息:")
            context_parts.append(f"{report['basic_info']}")
            context_parts.append("")
        
        # 添加任务说明
        context_parts.append("## 🎯 辩论任务:")
        context_parts.append("请基于以上所有专家的分析结果，进行深度讨论并最终投票决定该股票是看涨(bullish)还是看跌(bearish)。")
        context_parts.append("你需要引用具体的分析数据来支持你的观点，并与其他专家进行充分讨论。")
        
        full_context = "\n".join(context_parts)
        
        # 发送给所有agents
        for agent_id, agent in self.agents.items():
            if isinstance(agent, ToolCallAgent):
                agent.update_memory("user", full_context)
                self.llm_calls += 1
                logger.info(f"Sent comprehensive research context to {agent_id}")

    async def _run_structured_debate(self) -> None:
        """Run structured debate rounds with cumulative context passing."""
        for round_num in range(self.debate_rounds):
            self.state.current_round = round_num + 1
            logger.info(f"🗣️ Starting debate round {round_num + 1}/{self.debate_rounds}")
            
            # Run debate round with each agent speaking once
            for speaker_index, agent_id in enumerate(self.state.agent_order):
                if not self.state.can_agent_speak(agent_id):
                    logger.warning(f"⚠️ {agent_id} cannot speak (terminated)")
                    continue
                    
                self.state.current_speaker_index = speaker_index
                
                logger.info(f"📢 {agent_id} turn to speak (#{speaker_index + 1})")
                
                # 为当前发言者提供辩论指导
                await self._send_debate_instruction(agent_id, speaker_index, round_num)
                
                # 执行单个专家的发言轮次 (限制步数为1)
                await self._run_single_agent_debate_turn(agent_id)
    
    async def _send_debate_instruction(self, current_agent_id: str, speaker_index: int, round_num: int) -> None:
        """Send specific debate instruction to current speaker."""
        # 构建前面发言的总结
        previous_speeches = []
        for event in self.state.battle_history:
            if event.get("type") == "speak":
                speaker_name = event.get("agent_name", "Unknown")
                content = event.get("content", "")
                if content:
                    previous_speeches.append(f"**{speaker_name}**: {content[:200]}...")
        
        # 构建辩论指导
        context_parts = [
            f"# 🎯 第{round_num + 1}轮辩论发言 (你是第{speaker_index + 1}位发言者)",
            "",
            "**你的任务非常明确：**",
            "1. 立即使用Battle.speak发表你的观点（看涨或看跌）",
            "2. 引用研究阶段的具体数据支持你的立场", 
            "3. 回应前面专家的观点（支持或反驳）",
            "4. 发言后请立即投票（Battle.vote）- 你可以在每轮都投票！",
            "5. 如果其他专家的观点改变了你的看法，请更新你的投票",
            "",
            "💡 **动态投票机制**：你的每次投票都会覆盖之前的投票，最终以最后一次投票为准。",
            "⚠️ **严禁行为**：不要再做深度分析，直接基于已有数据发言！",
            ""
        ]
        
        if previous_speeches:
            context_parts.extend([
                "## 📋 前面专家的观点：",
                ""
            ])
            context_parts.extend(previous_speeches)
            context_parts.extend([
                "",
                "## 🗣️ 现在轮到你发言，请立即表态并说出理由！"
            ])
        else:
            context_parts.extend([
                "## 🗣️ 你是第一位发言者，请率先表明立场！",
                "直接说出你的观点：看涨还是看跌，并给出核心理由。"
            ])
        
        debate_instruction = "\n".join(context_parts)
        
        # 发送给当前发言的agent
        if current_agent_id in self.agents:
            agent = self.agents[current_agent_id]
            if isinstance(agent, ToolCallAgent):
                agent.update_memory("user", debate_instruction)
                self.llm_calls += 1
                logger.info(f"✉️ Sent debate instruction to {current_agent_id} (Round {round_num}, Speaker #{speaker_index + 1})")

    async def _run_single_agent_debate_turn(self, agent_id: str) -> None:
        """Run a single agent's debate turn with limited steps and retry mechanism."""
        if agent_id not in self.agents:
            logger.error(f"❌ Agent {agent_id} not found in agents")
            return
        
        agent = self.agents[agent_id]
        original_max_steps = agent.max_steps
        max_retries = 2  # 允许重试2次
        
        for attempt in range(max_retries + 1):
            try:
                # 限制步数为2，给agent更多机会
                agent.max_steps = 2
                agent.current_step = 0
                agent.state = AgentState.IDLE
                
                # 执行单步
                logger.info(f"🎤 {agent_id} speaking (attempt {attempt + 1}/{max_retries + 1})...")
                result = await agent.run(f"现在是你的发言时间，请立即使用Battle.speak表达观点！")
                logger.info(f"✅ {agent_id} completed speaking turn")
                break  # 成功则退出重试循环
                
            except Exception as e:
                logger.error(f"❌ Error in {agent_id} debate turn (attempt {attempt + 1}): {str(e)}")
                if attempt == max_retries:
                    logger.error(f"❌ {agent_id} failed all debate attempts, marking as problematic")
                    # 不标记为terminated，让agent继续参与投票
                else:
                    logger.info(f"🔄 Retrying {agent_id} debate turn...")
        
        # 恢复原始设置
        agent.max_steps = original_max_steps

    async def _run_final_voting(self) -> None:
        """Run final voting phase."""
        logger.info("🗳️ Starting final voting phase")
        
        # 获取所有应该投票的分析师
        eligible_voters = []
        for agent_id in self.state.active_agents.keys():
            if self.state.can_agent_vote(agent_id):
                eligible_voters.append(agent_id)
            else:
                logger.warning(f"⚠️ {agent_id} cannot vote: {'terminated' if agent_id in self.state.terminated_agents else 'unknown reason'}")
        
        logger.info(f"📊 Eligible voters: {eligible_voters} (total: {len(eligible_voters)})")
        
        # 为所有合格的分析师发送投票指令
        for agent_id in eligible_voters:
            # 检查是否已有最终投票
            if agent_id in self.state.final_votes:
                logger.info(f"✅ {agent_id} has final vote: {self.state.final_votes[agent_id]} - allowing update")
            else:
                logger.info(f"🗳️ {agent_id} needs to cast final vote")
            
            logger.info(f"🗳️ Requesting vote from {agent_id}")
            await self._send_voting_instruction(agent_id)
            await self._run_single_agent_voting_turn(agent_id)
        
        # 最终验证：确保所有合格的分析师都投了票
        missing_votes = []
        for agent_id in eligible_voters:
            if agent_id not in self.state.final_votes:
                missing_votes.append(agent_id)
        
        if missing_votes:
            logger.error(f"❌ CRITICAL: Missing votes after voting phase: {missing_votes}")
            # 对缺失投票的分析师进行最后一次尝试
            for agent_id in missing_votes:
                logger.warning(f"🔄 Final attempt to get vote from {agent_id}")
                await self._run_single_agent_voting_turn(agent_id)
        
        logger.info(f"✅ Final voting phase completed. Total votes: {len(self.state.final_votes)}")

    async def _send_voting_instruction(self, agent_id: str) -> None:
        """Send voting instruction to agent."""
        voting_instruction = f"""
# 🗳️ 最终投票确认时间！

基于所有轮次的辩论和你的专业分析，现在是你最后一次确认或更新投票的机会。

**你的当前投票状态：**
{f"✅ 已投票: {self.state.final_votes[agent_id]}" if agent_id in self.state.final_votes else "⚠️ 尚未投票"}

**请立即使用Battle.vote工具投票：**
- 看涨：Battle.vote("bullish")  
- 看跌：Battle.vote("bearish")

**然后使用Terminate结束参与。**

💡 如果你在辩论过程中改变了看法，现在可以更新你的投票！
⚠️ 不要再分析，直接投票！
        """
        
        if agent_id in self.agents:
            agent = self.agents[agent_id]
            if isinstance(agent, ToolCallAgent):
                agent.update_memory("user", voting_instruction)
                self.llm_calls += 1
                logger.info(f"📮 Sent voting instruction to {agent_id}")

    async def _run_single_agent_voting_turn(self, agent_id: str) -> None:
        """Run a single agent's voting turn with enhanced retry mechanism."""
        if agent_id not in self.agents:
            logger.error(f"❌ Agent {agent_id} not found in agents")
            return
        
        agent = self.agents[agent_id]
        original_max_steps = agent.max_steps
        max_retries = 5  # 增加重试次数，确保投票成功
        
        for attempt in range(max_retries + 1):
            try:
                # 限制步数为2，给agent更多机会
                agent.max_steps = 2
                agent.current_step = 0
                agent.state = AgentState.IDLE
                
                logger.info(f"🗳️ {agent_id} voting (attempt {attempt + 1}/{max_retries + 1})...")
                result = await agent.run("请立即投票！")
                
                # 检查是否成功投票（使用新的final_votes机制）
                if agent_id in self.state.final_votes:
                    logger.info(f"✅ {agent_id} successfully voted: {self.state.final_votes[agent_id]}")
                    break
                else:
                    logger.warning(f"⚠️ {agent_id} completed run but no vote recorded")
                    if attempt == max_retries:
                        logger.error(f"❌ {agent_id} failed to vote after all attempts")
                        # 最后一次尝试：直接设置默认投票
                        logger.warning(f"🔧 Setting default 'bearish' vote for {agent_id} to ensure participation")
                        self.state.record_vote(agent_id, "bearish", self.state.current_round)
                
            except Exception as e:
                logger.error(f"❌ Error in {agent_id} voting (attempt {attempt + 1}): {str(e)}")
                if attempt == max_retries:
                    logger.error(f"❌ {agent_id} failed all voting attempts")
                    # 最后一次尝试：直接设置默认投票
                    logger.warning(f"🔧 Setting default 'bearish' vote for {agent_id} due to persistent errors")
                    self.state.record_vote(agent_id, "bearish", self.state.current_round)
                else:
                    logger.info(f"🔄 Retrying {agent_id} voting...")
        
        agent.max_steps = original_max_steps
    
    def _validate_final_voting(self) -> None:
        """验证最终投票统计的正确性"""
        logger.info("🔍 Validating final voting results...")
        
        # 获取所有应该参与投票的专家
        expected_voters = []
        missing_voters = []
        
        for agent_id in self.state.active_agents.keys():
            if agent_id not in self.state.terminated_agents:
                expected_voters.append(agent_id)
                if agent_id not in self.state.final_votes:
                    missing_voters.append(agent_id)
        
        logger.info(f"📊 Expected voters: {expected_voters} (total: {len(expected_voters)})")
        logger.info(f"📊 Actual voters: {list(self.state.final_votes.keys())} (total: {len(self.state.final_votes)})")
        
        if missing_voters:
            logger.error(f"❌ Missing votes from: {missing_voters}")
            logger.error(f"❌ This explains why we have {len(self.state.final_votes)} votes instead of {len(expected_voters)}")
        
        # 验证投票选项的有效性
        invalid_votes = []
        for agent_id, vote in self.state.final_votes.items():
            if vote not in VOTE_OPTIONS:
                invalid_votes.append(f"{agent_id}: {vote}")
        
        if invalid_votes:
            logger.error(f"❌ Invalid vote options found: {invalid_votes}")
        
        # 重新强制计算投票结果（以防有遗漏）
        self.state._recalculate_vote_results()
        
        total_votes = sum(self.state.vote_results.values())
        expected_vote_count = len(expected_voters) - len(self.state.terminated_agents)
        logger.info(f"✅ Final validation: {total_votes} total votes from {len(expected_voters)} expected experts")
        
        if total_votes != expected_vote_count:
            logger.error(f"❌ VOTE COUNT MISMATCH: Expected {expected_vote_count} votes, got {total_votes}")
            # 尝试修复：如果agent_order为空但有active_agents，重建agent_order
            if not self.state.agent_order and self.state.active_agents:
                logger.warning("🔧 Attempting to fix empty agent_order...")
                self.state.agent_order = list(self.state.active_agents.keys())
                logger.info(f"🔧 Rebuilt agent_order: {self.state.agent_order}")

    def _prepare_results(self) -> Dict[str, Any]:
        """Prepare battle results with enhanced voting data."""
        # 最终统计验证
        self._validate_final_voting()
        
        # 计算最终决策
        bullish_votes = self.state.vote_results.get('bullish', 0)
        bearish_votes = self.state.vote_results.get('bearish', 0)
        final_decision = 'bullish' if bullish_votes > bearish_votes else 'bearish'
        
        return {
            "battle_history": self.state.battle_history,
            "debate_history": self.state.debate_history,
            "debate_rounds": self.debate_rounds,  # 辩论轮次
            "agent_order": self.state.agent_order,  # 分析师顺序
            "vote_results": self.state.vote_results,
            "vote_count": {
                "bullish": bullish_votes,
                "bearish": bearish_votes
            },
            "final_decision": final_decision,
            "round_votes": self.state.round_votes,  # 每轮投票历史
            "final_votes": self.state.final_votes,  # 最终投票结果
            "battle_highlights": self.state.battle_highlights,
            "total_tool_calls": self.tool_calls,
            "total_llm_calls": self.llm_calls,
            "voting_summary": {
                "total_experts": len(self.state.active_agents),
                "voted_experts": len(self.state.final_votes),
                "terminated_experts": len(self.state.terminated_agents),
                "rounds_with_votes": len(self.state.round_votes)
            }
        }

    async def _broadcast_message(self, sender_id: str, content: str, event_type: str) -> None:
        """Broadcast message to all active agents."""
        message = get_broadcast_message(
            sender_name=self.state.active_agents[sender_id],
            content=content,
            action_type=event_type,
        )
        
        for agent_id, agent in self.agents.items():
            if agent_id != sender_id and isinstance(agent, ToolCallAgent):
                agent.update_memory("user", message)
                self.llm_calls += 1
