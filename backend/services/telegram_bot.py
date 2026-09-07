"""
Telegram Bot Handler - Receives trading signals and stores in knowledge exchange
"""

import logging
import re
import json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler

logger = logging.getLogger(__name__)

class TelegramBotHandler:
    """Handles Telegram bot commands and signals"""
    
    def __init__(self, token, agent_manager, db_manager, app):
        self.token = token
        self.agent_manager = agent_manager
        self.db_manager = db_manager
        self.app = app
        self.application = None
        
    async def start_command(self, update: Update, context: CallbackContext):
        """Handle /start command"""
        welcome_message = """
🤖 *Trading Agent Platform Bot*

Welcome to the Trading Signal Bot!

*Available Commands:*
/help - Show this help message
/status - Get agent status
/agents - List all agents
/teach <topic> <content> - Teach all agents
/knowledge - Show recent knowledge exchanges

*How to send a signal:*
Just send a message in this format:
`BTCUSD BUY 50000 SL 49500 TP 51000`

*Example:*
`BTCUSD BUY 50000 SL 49500 TP 51000`

The signal will be sent to all 5 agents for voting!
        """
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: CallbackContext):
        """Handle /help command"""
        help_text = """
📚 *Trading Bot Commands*

/signal <asset> <action> <price> [SL] [TP]
    - Send a trading signal
    - Example: /signal BTCUSD BUY 50000

/status - Show current agent status
/agents - List all agents with their stats
/teach <topic> <content> - Teach all agents
/knowledge - Show recent knowledge exchanges

*Signal Format Examples:*
• `BTCUSD BUY 50000 SL 49500 TP 51000`
• `ETHUSD SELL 3000`
• `GOLD BUY 2350`
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def status_command(self, update: Update, context: CallbackContext):
        """Handle /status command - show agent status"""
        agents = self.agent_manager.get_all_status()
        
        message = "📊 *Agent Status Report*\n\n"
        for agent in agents:
            message += f"🤖 *{agent['name']}*\n"
            message += f"   XP: {agent['xp_points']} | Tokens: {agent['token_balance']}\n"
            message += f"   Accuracy: {agent['vote_accuracy']}% | Weight: {agent['trust_weight']:.2f}\n\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def agents_command(self, update: Update, context: CallbackContext):
        """Handle /agents command - list all agents"""
        agents = self.agent_manager.get_all_status()
        
        message = "🤖 *Trading Agents*\n\n"
        for agent in agents:
            message += f"🟢 *{agent['name']}* - {agent.get('type', 'Trading Agent')}\n"
            message += f"   📊 Accuracy: {agent['vote_accuracy']}%\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def teach_command(self, update: Update, context: CallbackContext):
        """Handle /teach command - teach all agents and store in knowledge exchange"""
        args = context.args
        if len(args) < 2:
            await update.message.reply_text("Usage: /teach <topic> <content>")
            return
        
        topic = args[0]
        content = ' '.join(args[1:])
        
        # Teach all agents
        agents = self.agent_manager.get_all_agents()
        for agent in agents:
            agent.learn_from_lesson(content)
            agent.xp_points += 25
            agent.token_balance += 5
            agent.knowledge_shared_count += 1
        
        # Store in knowledge exchange (app config)
        if not hasattr(self.app, 'knowledge_exchanges'):
            self.app.knowledge_exchanges = []
        
        knowledge_entry = {
            'id': len(self.app.knowledge_exchanges) + 1,
            'from_agent': f'Telegram_{update.effective_user.username or update.effective_user.id}',
            'to_agent': 'ALL AGENTS',
            'topic': f'📢 [TELEGRAM] {topic}',
            'content': content,
            'xp_reward': 25,
            'token_reward': 5,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'is_broadcast': True,
            'source': 'telegram'
        }
        self.app.knowledge_exchanges.insert(0, knowledge_entry)
        
        # Keep only last 100
        if len(self.app.knowledge_exchanges) > 100:
            self.app.knowledge_exchanges = self.app.knowledge_exchanges[:100]
        
        await update.message.reply_text(
            f"✅ *Teaching Complete!*\n\n"
            f"Topic: {topic}\n"
            f"All {len(agents)} agents learned and gained +25 XP, +5 Tokens!\n\n"
            f"📚 Knowledge has been added to the exchange.",
            parse_mode='Markdown'
        )
    
    async def knowledge_command(self, update: Update, context: CallbackContext):
        """Handle /knowledge command - show recent knowledge exchanges"""
        if not hasattr(self.app, 'knowledge_exchanges') or not self.app.knowledge_exchanges:
            await update.message.reply_text("📚 No knowledge exchanges yet. Use /teach to share knowledge!")
            return
        
        exchanges = self.app.knowledge_exchanges[:10]
        message = "📚 *Recent Knowledge Exchanges*\n\n"
        
        for ex in exchanges:
            message += f"📖 *{ex.get('topic', 'Knowledge')}*\n"
            message += f"   From: {ex.get('from_agent')} → To: {ex.get('to_agent')}\n"
            message += f"   Content: {ex.get('content', '')[:100]}...\n"
            message += f"   Reward: +{ex.get('xp_reward', 0)} XP\n\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def parse_signal_message(self, message_text: str) -> dict:
        """Parse natural language trading signal"""
        
        message_text = message_text.upper().strip()
        
        # Pattern: ASSET ACTION PRICE
        pattern1 = r'^(\w+)\s+(BUY|SELL)\s+(\d+(?:\.\d+)?)$'
        match1 = re.match(pattern1, message_text)
        
        if match1:
            return {
                'asset': match1.group(1),
                'action': match1.group(2),
                'price': float(match1.group(3)),
                'stoploss': None,
                'takeprofit': None,
                'confidence': 70,
                'strength': 'SIGNAL'
            }
        
        # Pattern: ASSET ACTION PRICE SL STOP TP TAKE
        pattern2 = r'^(\w+)\s+(BUY|SELL)\s+(\d+(?:\.\d+)?)\s+(?:SL|STOP)\s+(\d+(?:\.\d+)?)\s+(?:TP|TAKE)\s+(\d+(?:\.\d+)?)$'
        match2 = re.match(pattern2, message_text)
        
        if match2:
            return {
                'asset': match2.group(1),
                'action': match2.group(2),
                'price': float(match2.group(3)),
                'stoploss': float(match2.group(4)),
                'takeprofit': float(match2.group(5)),
                'confidence': 85,
                'strength': 'STRONG_SIGNAL'
            }
        
        return None
    
    async def handle_message(self, update: Update, context: CallbackContext):
        """Handle incoming messages (trading signals)"""
        
        message_text = update.message.text
        user = update.effective_user
        chat_id = update.effective_chat.id
        
        # Skip commands
        if message_text.startswith('/'):
            return
        
        # Parse the signal
        signal_data = await self.parse_signal_message(message_text)
        
        if not signal_data:
            await update.message.reply_text(
                "❌ *Invalid signal format!*\n\n"
                "Use format:\n"
                "`BTCUSD BUY 50000`\n"
                "or\n"
                "`BTCUSD BUY 50000 SL 49500 TP 51000`\n\n"
                "Send /help for more info",
                parse_mode='Markdown'
            )
            return
        
        # Add metadata
        signal_data['raw_message'] = message_text
        signal_data['user_id'] = user.id
        signal_data['username'] = user.username or user.first_name
        signal_data['chat_id'] = chat_id
        signal_data['received_at'] = datetime.now().isoformat()
        
        # Store in knowledge exchange as a signal
        if not hasattr(self.app, 'knowledge_exchanges'):
            self.app.knowledge_exchanges = []
        
        signal_entry = {
            'id': len(self.app.knowledge_exchanges) + 1,
            'from_agent': f'📡 Signal from {signal_data["username"]}',
            'to_agent': 'ALL AGENTS',
            'topic': f'🎯 Trading Signal: {signal_data["asset"]} {signal_data["action"]}',
            'content': f"Price: ${signal_data['price']:,.2f}\n"
                      f"Confidence: {signal_data['confidence']}% ({signal_data['strength']})\n"
                      f"Raw: {message_text}",
            'xp_reward': 0,
            'token_reward': 0,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'is_signal': True,
            'signal_data': signal_data
        }
        self.app.knowledge_exchanges.insert(0, signal_entry)
        
        # Notify user
        await update.message.reply_text(
            f"📡 *Signal Received!*\n\n"
            f"Asset: {signal_data['asset']}\n"
            f"Action: {signal_data['action']}\n"
            f"Price: ${signal_data['price']:,.2f}\n"
            f"Confidence: {signal_data['confidence']}% ({signal_data['strength']})\n\n"
            f"🔄 Sending to {len(self.agent_manager.get_all_agents())} agents for voting...",
            parse_mode='Markdown'
        )
        
        # Collect votes from all agents
        votes = await self.collect_agent_votes(signal_data)
        
        # Store voting results in knowledge exchange
        vote_entry = {
            'id': len(self.app.knowledge_exchanges) + 1,
            'from_agent': 'Voting System',
            'to_agent': 'ALL AGENTS',
            'topic': f'🗳️ Voting Results: {signal_data["asset"]}',
            'content': f"Final Decision: {votes['final_decision']}\n"
                      f"BUY: {votes['buy_percent']}% ({votes['buy_votes']} votes)\n"
                      f"SELL: {votes['sell_percent']}% ({votes['sell_votes']} votes)\n"
                      f"HOLD: {votes['hold_percent']}% ({votes['hold_votes']} votes)",
            'xp_reward': 0,
            'token_reward': 0,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'is_vote_result': True
        }
        self.app.knowledge_exchanges.insert(0, vote_entry)
        
        # Send vote results
        await self.send_vote_results(update, signal_data, votes)
    
    async def collect_agent_votes(self, signal_data: dict) -> dict:
        """Collect votes from all agents"""
        
        # Prepare market features (simplified for demo)
        market_features = {
            'z_score_20': 0.5,
            'z_score_50': 0.3,
            'rsi_14': 55,
            'rsi_slope_5': 0.2,
            'trend_strength': 60,
            'volume_zscore': 1.2,
            'spread_ratio': 0.008
        }
        
        votes = self.agent_manager.collect_votes(signal_data, market_features)
        
        # Calculate voting results
        buy_votes = sum(1 for v in votes.values() if v['vote'] == 'BUY')
        sell_votes = sum(1 for v in votes.values() if v['vote'] == 'SELL')
        hold_votes = sum(1 for v in votes.values() if v['vote'] == 'HOLD')
        total = len(votes)
        
        # Calculate weighted decision
        weighted_buy = sum(v['confidence'] for v in votes.values() if v['vote'] == 'BUY')
        weighted_sell = sum(v['confidence'] for v in votes.values() if v['vote'] == 'SELL')
        
        if weighted_buy > weighted_sell:
            final_decision = 'BUY'
            final_confidence = weighted_buy / total if total > 0 else 0
        elif weighted_sell > weighted_buy:
            final_decision = 'SELL'
            final_confidence = weighted_sell / total if total > 0 else 0
        else:
            final_decision = 'HOLD'
            final_confidence = 50
        
        return {
            'votes': votes,
            'buy_votes': buy_votes,
            'sell_votes': sell_votes,
            'hold_votes': hold_votes,
            'buy_percent': round(buy_votes / total * 100, 1) if total > 0 else 0,
            'sell_percent': round(sell_votes / total * 100, 1) if total > 0 else 0,
            'hold_percent': round(hold_votes / total * 100, 1) if total > 0 else 0,
            'final_decision': final_decision,
            'final_confidence': round(final_confidence, 1),
            'total_agents': total
        }
    
    async def send_vote_results(self, update: Update, signal_data: dict, votes_result: dict):
        """Send voting results to Telegram"""
        
        # Create vote bars
        buy_bar = "🟢" * int(votes_result['buy_percent'] / 10)
        sell_bar = "🔴" * int(votes_result['sell_percent'] / 10)
        hold_bar = "⚪" * int(votes_result['hold_percent'] / 10)
        
        message = f"🗳️ *Voting Results*\n\n"
        message += f"📊 *Signal:* {signal_data['action']} {signal_data['asset']} @ ${signal_data['price']:,.2f}\n\n"
        message += f"*Vote Distribution:*\n"
        message += f"BUY:  {buy_bar} {votes_result['buy_percent']}% ({votes_result['buy_votes']} votes)\n"
        message += f"SELL: {sell_bar} {votes_result['sell_percent']}% ({votes_result['sell_votes']} votes)\n"
        message += f"HOLD: {hold_bar} {votes_result['hold_percent']}% ({votes_result['hold_votes']} votes)\n\n"
        
        # Individual agent votes
        message += f"*Agent Votes:*\n"
        for agent_name, vote_data in votes_result['votes'].items():
            vote_icon = "🟢" if vote_data['vote'] == 'BUY' else "🔴" if vote_data['vote'] == 'SELL' else "⚪"
            message += f"{vote_icon} {agent_name}: {vote_data['vote']} ({vote_data['confidence']:.0f}%)\n"
        
        message += f"\n*Final Decision:* "
        if votes_result['final_decision'] == 'BUY':
            message += f"🟢 BUY"
        elif votes_result['final_decision'] == 'SELL':
            message += f"🔴 SELL"
        else:
            message += f"⚪ HOLD"
        
        message += f" (Confidence: {votes_result['final_confidence']}%)"
        
        # Add action buttons
        keyboard = [
            [
                InlineKeyboardButton("✅ Execute Trade", callback_data="execute"),
                InlineKeyboardButton("❌ Reject", callback_data="reject")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)
    
    async def button_callback(self, update: Update, context: CallbackContext):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == 'execute':
            await query.edit_message_text("✅ Trade execution confirmed!")
        elif data == 'reject':
            await query.edit_message_text("❌ Trade rejected.")
    
    async def start_bot(self):
        """Start the Telegram bot"""
        try:
            self.application = Application.builder().token(self.token).build()
            
            # Add handlers
            self.application.add_handler(CommandHandler("start", self.start_command))
            self.application.add_handler(CommandHandler("help", self.help_command))
            self.application.add_handler(CommandHandler("status", self.status_command))
            self.application.add_handler(CommandHandler("agents", self.agents_command))
            self.application.add_handler(CommandHandler("teach", self.teach_command))
            self.application.add_handler(CommandHandler("knowledge", self.knowledge_command))
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
            self.application.add_handler(CallbackQueryHandler(self.button_callback))
            
            # Start polling
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            logger.info("✅ Telegram bot started successfully!")
            print("✅ Telegram bot is running! Send a message to your bot on Telegram.")
            
            return self.application
        except Exception as e:
            logger.error(f"Failed to start Telegram bot: {e}")
            print(f"❌ Telegram bot error: {e}")
            return None
