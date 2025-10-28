import plaid
from plaid.api import plaid_api
from plaid.model import *
from plaid.exceptions import ApiException
import logging
from app.config import settings
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class PlaidClient:
    def __init__(self):
        self.configuration = self._create_configuration()
        self.client = plaid_api.PlaidApi(plaid.ApiClient(self.configuration))
        self.environment = settings.PLAID_ENVIRONMENT
    
    def _create_configuration(self):
        host_map = {
            "sandbox": plaid.Environment.Sandbox,
            "development": plaid.Environment.Development,
            "production": plaid.Environment.Production
        }
        
        configuration = plaid.Configuration(
            host=host_map.get(settings.PLAID_ENVIRONMENT, plaid.Environment.Sandbox),
            api_key={
                'clientId': settings.PLAID_CLIENT_ID,
                'secret': settings.PLAID_SECRET,
            }
        )
        return configuration
    
    async def create_link_token(self, user_id: str, client_name: str = "FinHealth360") -> Dict[str, Any]:
        """Create Link token for frontend"""
        try:
            request = LinkTokenCreateRequest(
                user=LinkTokenCreateRequestUser(client_user_id=user_id),
                client_name=client_name,
                products=[Products('transactions'), Products('auth')],
                country_codes=[CountryCode('US')],
                language='en',
            )
            
            # Add webhook if configured
            if settings.WEBHOOK_BASE_URL:
                request['webhook'] = f"{settings.WEBHOOK_BASE_URL}/webhooks/plaid"
            
            response = self.client.link_token_create(request)
            logger.info(f"Link token created for user: {user_id}")
            return response.to_dict()
            
        except ApiException as e:
            logger.error(f"Plaid API error creating link token: {e}")
            raise
    
    async def exchange_public_token(self, public_token: str) -> Dict[str, Any]:
        """Exchange public token for access token"""
        try:
            request = ItemPublicTokenExchangeRequest(public_token=public_token)
            response = self.client.item_public_token_exchange(request)
            logger.info("Public token exchanged successfully")
            return response.to_dict()
        except ApiException as e:
            logger.error(f"Plaid API error exchanging public token: {e}")
            raise
    
    async def get_transactions_sync(self, access_token: str, cursor: Optional[str] = None) -> Dict[str, Any]:
        """Get transactions using sync API (recommended)"""
        try:
            request = TransactionsSyncRequest(
                access_token=access_token,
                cursor=cursor
            )
            response = self.client.transactions_sync(request)
            return response.to_dict()
        except ApiException as e:
            logger.error(f"Plaid API error syncing transactions: {e}")
            raise
    
    async def get_accounts(self, access_token: str) -> Dict[str, Any]:
        """Get account information"""
        try:
            request = AccountsGetRequest(access_token=access_token)
            response = self.client.accounts_get(request)
            return response.to_dict()
        except ApiException as e:
            logger.error(f"Plaid API error getting accounts: {e}")
            raise
    
    async def get_item_info(self, access_token: str) -> Dict[str, Any]:
        """Get item information"""
        try:
            request = ItemGetRequest(access_token=access_token)
            response = self.client.item_get(request)
            return response.to_dict()
        except ApiException as e:
            logger.error(f"Plaid API error getting item info: {e}")
            raise
    
    async def remove_item(self, access_token: str) -> Dict[str, Any]:
        """Remove Plaid item"""
        try:
            request = ItemRemoveRequest(access_token=access_token)
            response = self.client.item_remove(request)
            logger.info("Plaid item removed successfully")
            return response.to_dict()
        except ApiException as e:
            logger.error(f"Plaid API error removing item: {e}")
            raise
    
    async def get_webhook_verification_key(self, key_id: str) -> Dict[str, Any]:
        """Get webhook verification key"""
        try:
            request = WebhookVerificationKeyGetRequest(key_id=key_id)
            response = self.client.webhook_verification_key_get(request)
            return response.to_dict()
        except ApiException as e:
            logger.error(f"Plaid API error getting webhook key: {e}")
            raise

plaid_client = PlaidClient()