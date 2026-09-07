"""
Trading Cards API Routes
Reads from user_auth_db.trading_cards table
"""

from fastapi import APIRouter, HTTPException, Depends, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
import jwt

from pydantic import BaseModel
import uuid

from src.database.supabase_client import get_user_auth_service, get_trading_service
from src.api.routes.client_auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()


# ============================================================
# CARD MODELS (Pydantic)
# ============================================================

class CardCreate(BaseModel):
    card_id: str
    card_pin: str
    username: str


class CardRedeemRequest(BaseModel):
    card_id: str
    card_pin: str


# ============================================================
# HELPERS
# ============================================================

def sanitize_card(card: Dict[str, Any]) -> Dict[str, Any]:
    """Remove sensitive data from card response"""
    if not card:
        return {}
    sensitive = {"card_pin"}
    return {key: value for key, value in card.items() if key not in sensitive}

@router.get("/cards")
async def get_user_cards(
    user: dict = Depends(get_current_user)
):
    """Get all cards for the current user"""
    try:
        auth_db = get_user_auth_service()
        user_id_str = str(user['id'])
        
        # ✅ Get cards where used_by matches the user
        result = auth_db.client.table('trading_cards')\
            .select('*')\
            .eq('used_by', user_id_str)\
            .order('created_at', desc=True)\
            .execute()
        
        # ✅ Handle empty result
        cards = []
        if result.data:
            for card in result.data:
                cards.append({
                    'id': card.get('id'),
                    'card_id': card.get('card_id'),
                    'username': card.get('username'),
                    'amount': float(card.get('amount', 0)),
                    'is_used': card.get('is_used', False),
                    'is_active': card.get('is_active', True),
                    'created_at': card.get('created_at'),
                    'used_at': card.get('used_at')
                })
        
        total_amount = sum(c.get('amount', 0) for c in cards)
        
        return {
            "success": True,
            "cards": cards,
            "count": len(cards),
            "total_amount": round(total_amount, 2)
        }
        
    except Exception as e:
        logger.error(f"❌ Get cards error: {e}")
        import traceback
        traceback.print_exc()
        # ✅ Return a proper error response instead of crashing
        return {
            "success": False,
            "error": str(e),
            "cards": [],
            "count": 0,
            "total_amount": 0
        }
# ============================================================
# ✅ FIXED: CREATE CARD ENDPOINT
# ============================================================

@router.post("/cards", status_code=status.HTTP_201_CREATED)
async def create_client_card(
    request: Request,
    user: dict = Depends(get_current_user)
):
    """
    Add/Validate a trading card from user_auth_db.trading_cards
    ✅ FIXED: Properly handles JSON and form data
    ✅ FIXED: Adds card to user's list without requiring redeem
    """
    try:
        # Parse request body
        content_type = request.headers.get("content-type", "")
        
        if "application/json" in content_type:
            payload = await request.json()
        else:
            form_data = await request.form()
            payload = dict(form_data)
        
        card_id = str(payload.get("card_id", "") or "").strip()
        card_pin = str(payload.get("card_pin", "") or "").strip()
        username = str(payload.get("username", "") or "").strip()
        
        user_id_str = str(user['id'])
        user_email = user.get('email', 'unknown')
        
        logger.info(f"📡 Card validation request: {card_id} by user: {user_email}")
        
        if not card_id or not card_pin:
            raise HTTPException(status_code=400, detail="Card ID and PIN are required")
        
        if not username or len(username) < 2:
            raise HTTPException(status_code=400, detail="Card holder name is required")
        
        if len(card_id) != 8 or not card_id.isdigit():
            raise HTTPException(status_code=400, detail="Card ID must be exactly 8 digits")
        
        if len(card_pin) != 4 or not card_pin.isdigit():
            raise HTTPException(status_code=400, detail="PIN must be exactly 4 digits")
        
        # ✅ READ FROM USER_AUTH_DB.trading_cards
        auth_db = get_user_auth_service()
        
        # Check if card exists
        result = auth_db.client.table('trading_cards')\
            .select('*')\
            .eq('card_id', card_id)\
            .eq('card_pin', card_pin)\
            .execute()
        
        if not result.data:
            logger.warning(f"❌ Card not found: {card_id}")
            raise HTTPException(status_code=404, detail="Card not found. Please check the card number and PIN.")
        
        card = result.data[0]
        logger.info(f"✅ Card found: {card_id}, Amount: ${card.get('amount', 0)}")
        
        # ✅ Validate card holder name when available
        card_username = str(card.get('username') or '').strip()
        if card_username and card_username.upper() != username.upper():
            logger.warning(f"❌ Card holder mismatch: request={username} card={card_username}")
            raise HTTPException(status_code=400, detail="Card holder name does not match")
        
        # ✅ Check if card is already used
        if card.get('is_used', False):
            used_by = card.get('used_by')
            if used_by and str(used_by) == user_id_str:
                # Card was already redeemed by this user - return it
                logger.info(f"ℹ️ Card already redeemed by this user: {card_id}")
                return {
                    "success": True,
                    "message": "Card already in your account",
                    "card": {
                        "card_id": card.get('card_id'),
                        "username": card.get('username'),
                        "amount": float(card.get('amount', 0)),
                        "is_active": card.get('is_active', True),
                        "is_used": card.get('is_used', True)
                    }
                }
            raise HTTPException(status_code=400, detail="Card has already been used by another user")
        
        # ✅ Check if card is inactive
        if not card.get('is_active', True):
            raise HTTPException(status_code=400, detail="Card is inactive")
        
        # ✅ FIX: Claim the card for this user (add to their account)
        # This makes the card appear in /cards/user without needing redeem
        claim_result = auth_db.client.table('trading_cards')\
            .update({
                'used_by': user_id_str,
                'is_active': True,
                'is_used': False,  # Not used yet, just claimed
                'synced_to_trading': False
            })\
            .eq('card_id', card_id)\
            .select('*')\
            .execute()
        
        if not claim_result.data:
            logger.error(f"❌ Failed to claim card: {card_id}")
            raise HTTPException(status_code=500, detail="Could not claim card")
        
        updated_card = claim_result.data[0]
        amount = float(updated_card.get('amount', 0))
        
        logger.info(f"✅ Card claimed by user {user_id_str}: {card_id} (${amount})")
        
        # ✅ Also add the amount to the user's balance immediately
        if amount > 0:
            try:
                trading_db = get_trading_service()
                
                # Check if trading_balance exists
                balance_result = trading_db.client.table('trading_balances')\
                    .select('*')\
                    .eq('user_id', user_id_str)\
                    .execute()
                
                if balance_result.data:
                    # Update existing balance
                    current_balance = float(balance_result.data[0].get('balance', 0))
                    new_balance = current_balance + amount
                    
                    trading_db.client.table('trading_balances')\
                        .update({
                            'balance': new_balance,
                            'equity': new_balance,
                            'total_deposited': float(balance_result.data[0].get('total_deposited', 0)) + amount,
                            'last_card_deposit_at': datetime.now().isoformat(),
                            'updated_at': datetime.now().isoformat()
                        })\
                        .eq('user_id', user_id_str)\
                        .execute()
                    
                    logger.info(f"✅ Added ${amount} to user {user_id_str} balance. New: ${new_balance}")
                else:
                    # Create new balance
                    trading_db.client.table('trading_balances')\
                        .insert({
                            'user_id': user_id_str,
                            'balance': amount,
                            'equity': amount,
                            'total_deposited': amount,
                            'last_card_deposit_at': datetime.now().isoformat(),
                            'is_logged_in': True,
                            'login_count': 1,
                            'created_at': datetime.now().isoformat(),
                            'updated_at': datetime.now().isoformat()
                        })\
                        .execute()
                    
                    logger.info(f"✅ Created new balance for user {user_id_str}: ${amount}")
                
            except Exception as e:
                logger.error(f"❌ Failed to add balance: {e}")
                # Don't fail the request, just log the error
        
        return {
            "success": True,
            "message": f"Card validated! ${amount} added to your account",
            "card": {
                "card_id": updated_card.get('card_id'),
                "username": updated_card.get('username'),
                "amount": amount,
                "is_active": updated_card.get('is_active', True),
                "is_used": updated_card.get('is_used', False)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Card validation error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
@router.post("/cards/update-amount")
async def update_card_amount(
    request: Request,
    user: dict = Depends(get_current_user)
):
    """Update the amount column in user_auth_db.trading_cards"""
    try:
        payload = await request.json()
        card_id = str(payload.get("card_id", "")).strip()
        new_amount = float(payload.get("amount", 0))
        
        user_id_str = str(user['id'])
        
        print(f"📡 UPDATE: card_id='{card_id}', amount=${new_amount}")
        
        if not card_id:
            return {"success": False, "error": "Card ID required"}
        
        auth_db = get_user_auth_service()
        
        # Find card
        result = auth_db.client.table('trading_cards')\
            .select('*')\
            .eq('card_id', card_id)\
            .execute()
        
        if not result.data:
            return {"success": False, "error": f"Card not found: {card_id}"}
        
        card = result.data[0]
        actual_card_id = card.get('card_id')
        
        # Update
        auth_db.client.table('trading_cards')\
            .update({'amount': new_amount})\
            .eq('card_id', actual_card_id)\
            .execute()
        
        return {
            "success": True,
            "message": f"Card amount updated to ${new_amount}",
            "data": {"card_id": actual_card_id, "amount": new_amount}
        }
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return {"success": False, "error": str(e)}
@router.get("/cards/debug")
async def debug_cards(
    user: dict = Depends(get_current_user)
):
    """Debug endpoint to see all cards for the current user"""
    try:
        auth_db = get_user_auth_service()
        user_id_str = str(user['id'])
        
        result = auth_db.client.table('trading_cards')\
            .select('*')\
            .eq('used_by', user_id_str)\
            .execute()
        
        return {
            "success": True,
            "cards": result.data if result.data else [],
            "count": len(result.data) if result.data else 0,
            "user_id": user_id_str
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
@router.get("/balance")
async def get_user_balance(
    user: dict = Depends(get_current_user)
):
    """
    Get user's total balance from trading_balances
    """
    try:
        user_id_str = str(user['id'])
        trading_db = get_trading_service()
        
        result = trading_db.client.table('trading_balances')\
            .select('*')\
            .eq('user_id', user_id_str)\
            .execute()
        
        if result.data:
            balance_data = result.data[0]
            return {
                "success": True,
                "balance": {
                    "balance": float(balance_data.get('balance', 0)),
                    "equity": float(balance_data.get('equity', 0)),
                    "total_deposited": float(balance_data.get('total_deposited', 0)),
                    "last_card_deposit_at": balance_data.get('last_card_deposit_at')
                }
            }
        else:
            return {
                "success": True,
                "balance": {
                    "balance": 0,
                    "equity": 0,
                    "total_deposited": 0
                }
            }
            
    except Exception as e:
        logger.error(f"❌ Get balance error: {e}")
        return {
            "success": False,
            "error": str(e),
            "balance": {
                "balance": 0,
                "equity": 0,
                "total_deposited": 0
            }
        }
@router.post("/cards/redeem")
async def redeem_card(
    request: Request,
    user: dict = Depends(get_current_user)
):
    """
    Redeem a card from user_auth_db.trading_cards
    """
    try:
        content_type = request.headers.get("content-type", "")
        
        if "application/json" in content_type:
            payload = await request.json()
        else:
            form_data = await request.form()
            payload = dict(form_data)
        
        card_id = str(payload.get("card_id", "") or "").strip()
        card_pin = str(payload.get("card_pin", "") or "").strip()
        user_id_str = str(user['id'])
        
        logger.info(f"📡 Redeem card request: {card_id} by user: {user.get('email')}")
        
        if not card_id or not card_pin:
            raise HTTPException(status_code=400, detail="Card ID and PIN are required")
        
        auth_db = get_user_auth_service()
        
        result = auth_db.client.table('trading_cards')\
            .select('*')\
            .eq('card_id', card_id)\
            .eq('card_pin', card_pin)\
            .execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Card not found")
        
        card = result.data[0]
        amount = float(card.get('amount', 0))
        
        # ✅ Check if card is already used
        if card.get('is_used', False):
            if str(card.get('used_by')) == user_id_str:
                raise HTTPException(status_code=400, detail="Card already redeemed by you")
            raise HTTPException(status_code=400, detail="Card already used by another user")
        
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Card has no redeemable amount")
        
        # ✅ MARK CARD AS USED
        auth_db.client.table('trading_cards')\
            .update({
                'is_used': True,
                'used_at': datetime.now().isoformat(),
                'synced_to_trading': True,
                'synced_at': datetime.now().isoformat()
            })\
            .eq('card_id', card_id)\
            .eq('used_by', user_id_str)\
            .execute()
        
        logger.info(f"✅ Card marked as used: {card_id}")
        
        # ✅ ADD BALANCE
        trading_db = get_trading_service()
        
        balance_result = trading_db.client.table('trading_balances')\
            .select('*')\
            .eq('user_id', user_id_str)\
            .execute()
        
        if balance_result.data:
            current_balance = float(balance_result.data[0].get('balance', 0))
            new_balance = current_balance + amount
            
            trading_db.client.table('trading_balances')\
                .update({
                    'balance': new_balance,
                    'equity': new_balance,
                    'total_deposited': float(balance_result.data[0].get('total_deposited', 0)) + amount,
                    'last_card_deposit_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                })\
                .eq('user_id', user_id_str)\
                .execute()
            
            logger.info(f"✅ Updated balance for user {user_id_str}: ${new_balance}")
        else:
            trading_db.client.table('trading_balances')\
                .insert({
                    'user_id': user_id_str,
                    'balance': amount,
                    'equity': amount,
                    'total_deposited': amount,
                    'last_card_deposit_at': datetime.now().isoformat(),
                    'is_logged_in': True,
                    'login_count': 1,
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                })\
                .execute()
            
            logger.info(f"✅ Created new balance for user {user_id_str}: ${amount}")
        
        return {
            "success": True,
            "message": f"Card redeemed! ${amount} added to your account",
            "amount": amount,
            "card": {
                "card_id": card.get('card_id'),
                "username": card.get('username'),
                "amount": amount
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Redeem card error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# GET USER CARDS - FIXED
# ============================================================

        cards = []
        for card in result.data:
            card_data = sanitize_card(card)
            cards.append(card_data)
        
        total_amount = sum(float(c.get('amount', 0)) for c in cards)
        
        return {
            "success": True,
            "cards": cards,
            "count": len(cards),
            "total_amount": round(total_amount, 2)
        }
        
    except Exception as e:
        logger.error(f"❌ Get user cards error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
@router.get("/cards/user")
async def get_user_cards_alias(
    user: dict = Depends(get_current_user)
):
    """Alias for /cards - gets cards for the current user"""
    return await get_user_cards(user)
@router.get("/my-cards")
async def get_my_cards(
    user: dict = Depends(get_current_user)
):
    """Get cards claimed by the current user"""
    try:
        auth_db = get_user_auth_service()
        user_id_str = str(user['id'])
        
        # Get cards where used_by matches the user
        result = auth_db.client.table('trading_cards')\
            .select('*')\
            .eq('used_by', user_id_str)\
            .order('created_at', desc=True)\
            .execute()
        
        cards = []
        for card in result.data:
            cards.append({
                'card_id': card.get('card_id'),
                'username': card.get('username'),
                'amount': float(card.get('amount', 0)),
                'is_used': card.get('is_used', False),
                'is_active': card.get('is_active', True),
                'created_at': card.get('created_at')
            })
        
        return {
            "success": True,
            "cards": cards,
            "count": len(cards),
            "total_amount": sum(c.get('amount', 0) for c in cards)
        }
    except Exception as e:
        logger.error(f"Get my cards error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
# ============================================================
# DELETE CARD - FIXED
# ============================================================

@router.delete("/cards/{card_id}")
async def delete_card(
    card_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Delete/Reset a card - deducts balance and resets card for reuse
    """
    try:
        logger.info(f"📡 Delete card request: {card_id} by user: {user.get('email')}")
        
        user_id_str = str(user['id'])
        auth_db = get_user_auth_service()
        
        # ✅ Find the card - don't filter by used_by yet
        result = auth_db.client.table('trading_cards')\
            .select('*')\
            .eq('card_id', card_id)\
            .execute()
        
        if not result.data:
            logger.warning(f"⚠️ Card not found: {card_id}")
            raise HTTPException(status_code=404, detail="Card not found")
        
        card = result.data[0]
        
        # ✅ Check if card belongs to this user OR is unclaimed
        card_used_by = card.get('used_by')
        if card_used_by and str(card_used_by) != user_id_str:
            logger.warning(f"⚠️ Card belongs to another user: {card_id}")
            raise HTTPException(status_code=403, detail="You cannot delete a card assigned to another user")
        
        amount = float(card.get('amount', 0))
        is_used = card.get('is_used', False)
        
        # ✅ Deduct balance only if card was used
        if is_used and amount > 0:
            trading_db = get_trading_service()
            balance_result = trading_db.client.table('trading_balances')\
                .select('*')\
                .eq('user_id', user_id_str)\
                .execute()
            
            if balance_result.data:
                current_balance = float(balance_result.data[0].get('balance', 0))
                new_balance = max(0, current_balance - amount)
                
                trading_db.client.table('trading_balances')\
                    .update({
                        'balance': new_balance,
                        'equity': new_balance,
                        'updated_at': datetime.now().isoformat()
                    })\
                    .eq('user_id', user_id_str)\
                    .execute()
                
                logger.info(f"✅ Deducted ${amount}. New balance: ${new_balance}")
        
        # ✅ RESET CARD for reuse
        auth_db.client.table('trading_cards')\
            .update({
                'is_used': False,
                'is_active': True,
                'used_by': None,
                'used_at': None,
                'synced_to_trading': False,
                'synced_at': None
            })\
            .eq('card_id', card.get('card_id'))\
            .execute()
        
        logger.info(f"✅ Card reset: {card_id}")
        
        return {
            "success": True,
            "message": f"Card {card_id} deleted and reset",
            "amount_deducted": amount if is_used else 0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Delete error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# ALIAS
# ============================================================
