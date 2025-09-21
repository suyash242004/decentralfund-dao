"""
DecentralFund DAO - Blockchain Service
Handles all blockchain interactions including smart contracts, Web3 operations,
and token management for the decentralized fund
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal
from datetime import datetime, timedelta
from dataclasses import dataclass

from web3 import Web3
from web3.contract import Contract
from web3.exceptions import ContractLogicError, TransactionNotFound
from eth_account import Account
import requests

from backend.config import settings

logger = logging.getLogger(__name__)

@dataclass
class ContractInfo:
    """Contract deployment information"""
    address: str
    abi: List[Dict]
    deployment_block: int

@dataclass
class TransactionResult:
    """Result of a blockchain transaction"""
    success: bool
    transaction_hash: str
    block_number: Optional[int] = None
    gas_used: Optional[int] = None
    error_message: Optional[str] = None

class BlockchainService:
    """Service for blockchain operations and smart contract interactions"""
    
    def __init__(self, provider_url: str):
        """Initialize blockchain service with Web3 provider"""
        self.web3 = Web3(Web3.HTTPProvider(provider_url))
        self.chain_id = settings.CHAIN_ID
        
        # Contract instances (will be loaded on first use)
        self.governance_token_contract: Optional[Contract] = None
        self.proposal_manager_contract: Optional[Contract] = None
        self.sip_manager_contract: Optional[Contract] = None
        self.fund_manager_registry_contract: Optional[Contract] = None
        self.decentralfund_contract: Optional[Contract] = None
        
        # Contract addresses (loaded from config/deployment)
        self.contract_addresses = {
            'governance_token': settings.GOVERNANCE_TOKEN_ADDRESS,
            'proposal_manager': settings.PROPOSAL_MANAGER_ADDRESS,
            'sip_manager': settings.SIP_MANAGER_ADDRESS,
            'fund_manager_registry': settings.FUND_MANAGER_REGISTRY_ADDRESS,
            'decentralfund': settings.DECENTRALFUND_ADDRESS
        }
        
        # Gas price strategy
        self.gas_price_strategy = 'medium'
        
        logger.info(f"🔗 Blockchain service initialized for chain {self.chain_id}")
    
    def is_connected(self) -> bool:
        """Check if Web3 connection is active"""
        try:
            return self.web3.is_connected()
        except Exception as e:
            logger.error(f"Connection check failed: {str(e)}")
            return False
    
    async def get_current_block_number(self) -> int:
        """Get current blockchain block number"""
        try:
            return self.web3.eth.block_number
        except Exception as e:
            logger.error(f"Error getting block number: {str(e)}")
            raise
    
    def load_contract(self, contract_name: str) -> Contract:
        """Load smart contract instance"""
        try:
            address = self.contract_addresses.get(contract_name)
            if not address:
                raise ValueError(f"Contract address not found for {contract_name}")
            
            # Load ABI from file or config
            abi = self._get_contract_abi(contract_name)
            
            contract = self.web3.eth.contract(
                address=Web3.to_checksum_address(address),
                abi=abi
            )
            
            logger.info(f"✅ Loaded {contract_name} contract at {address}")
            return contract
            
        except Exception as e:
            logger.error(f"Failed to load {contract_name} contract: {str(e)}")
            raise
    
    def _get_contract_abi(self, contract_name: str) -> List[Dict]:
        """Get contract ABI from storage"""
        # In production, load from files or IPFS
        # For demo, return simplified ABIs
        abis = {
            'governance_token': [
                {
                    "inputs": [{"name": "account", "type": "address"}],
                    "name": "balanceOf",
                    "outputs": [{"name": "", "type": "uint256"}],
                    "type": "function"
                },
                {
                    "inputs": [
                        {"name": "to", "type": "address"},
                        {"name": "amount", "type": "uint256"}
                    ],
                    "name": "mint",
                    "outputs": [{"name": "", "type": "bool"}],
                    "type": "function"
                },
                {
                    "inputs": [{"name": "account", "type": "address"}],
                    "name": "getVotingPower",
                    "outputs": [{"name": "", "type": "uint256"}],
                    "type": "function"
                }
            ],
            'proposal_manager': [
                {
                    "inputs": [
                        {"name": "title", "type": "string"},
                        {"name": "description", "type": "string"},
                        {"name": "options", "type": "string[]"},
                        {"name": "votingDuration", "type": "uint256"}
                    ],
                    "name": "createProposal",
                    "outputs": [{"name": "proposalId", "type": "uint256"}],
                    "type": "function"
                },
                {
                    "inputs": [
                        {"name": "proposalId", "type": "uint256"},
                        {"name": "option", "type": "uint256"},
                        {"name": "votingPower", "type": "uint256"}
                    ],
                    "name": "vote",
                    "outputs": [{"name": "", "type": "bool"}],
                    "type": "function"
                },
                {
                    "inputs": [{"name": "proposalId", "type": "uint256"}],
                    "name": "getProposalResults",
                    "outputs": [
                        {"name": "winningOption", "type": "uint256"},
                        {"name": "totalVotes", "type": "uint256"},
                        {"name": "isExecuted", "type": "bool"}
                    ],
                    "type": "function"
                }
            ],
            'sip_manager': [
                {
                    "inputs": [
                        {"name": "amount", "type": "uint256"},
                        {"name": "frequency", "type": "uint256"},
                        {"name": "duration", "type": "uint256"}
                    ],
                    "name": "createSIP",
                    "outputs": [{"name": "sipId", "type": "uint256"}],
                    "type": "function"
                },
                {
                    "inputs": [{"name": "sipId", "type": "uint256"}],
                    "name": "processSIPPayment",
                    "outputs": [{"name": "", "type": "bool"}],
                    "type": "function"
                }
            ]
        }
        
        return abis.get(contract_name, [])
    
    async def get_token_balance(self, wallet_address: str) -> float:
        """Get governance token balance for a wallet"""
        try:
            if not self.governance_token_contract:
                self.governance_token_contract = self.load_contract('governance_token')
            
            balance_wei = self.governance_token_contract.functions.balanceOf(
                Web3.to_checksum_address(wallet_address)
            ).call()
            
            # Convert from wei to tokens (assuming 18 decimals)
            balance = balance_wei / (10 ** 18)
            return float(balance)
            
        except Exception as e:
            logger.error(f"Error getting token balance: {str(e)}")
            return 0.0
    
    async def get_voting_power(self, wallet_address: str) -> float:
        """Get quadratic voting power for a wallet"""
        try:
            token_balance = await self.get_token_balance(wallet_address)
            # Quadratic voting: voting power = sqrt(token_balance)
            voting_power = token_balance ** 0.5
            return voting_power
            
        except Exception as e:
            logger.error(f"Error calculating voting power: {str(e)}")
            return 0.0
    
    async def mint_governance_tokens(self, to_address: str, amount: float) -> TransactionResult:
        """Mint governance tokens (for SIP investments)"""
        try:
            if not self.governance_token_contract:
                self.governance_token_contract = self.load_contract('governance_token')
            
            # Convert amount to wei
            amount_wei = int(amount * (10 ** 18))
            
            # Build transaction
            transaction = self.governance_token_contract.functions.mint(
                Web3.to_checksum_address(to_address),
                amount_wei
            ).build_transaction({
                'chainId': self.chain_id,
                'gas': 100000,
                'gasPrice': self.web3.to_wei('20', 'gwei'),
                'nonce': self.web3.eth.get_transaction_count(settings.FUND_WALLET_ADDRESS),
            })
            
            # Sign and send transaction
            signed_txn = self.web3.eth.account.sign_transaction(
                transaction, 
                private_key=settings.FUND_PRIVATE_KEY
            )
            
            tx_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
            
            return TransactionResult(
                success=receipt.status == 1,
                transaction_hash=tx_hash.hex(),
                block_number=receipt.blockNumber,
                gas_used=receipt.gasUsed
            )
            
        except Exception as e:
            logger.error(f"Error minting tokens: {str(e)}")
            return TransactionResult(
                success=False,
                transaction_hash="",
                error_message=str(e)
            )
    
    async def create_proposal(
        self, 
        creator_address: str,
        title: str,
        description: str,
        options: List[str],
        voting_duration_days: int = 7
    ) -> TransactionResult:
        """Create a new governance proposal"""
        try:
            if not self.proposal_manager_contract:
                self.proposal_manager_contract = self.load_contract('proposal_manager')
            
            voting_duration = voting_duration_days * 24 * 3600  # Convert to seconds
            
            # Build transaction
            transaction = self.proposal_manager_contract.functions.createProposal(
                title,
                description,
                options,
                voting_duration
            ).build_transaction({
                'chainId': self.chain_id,
                'gas': 200000,
                'gasPrice': self.web3.to_wei('20', 'gwei'),
                'nonce': self.web3.eth.get_transaction_count(creator_address),
            })
            
            # Note: In production, this would be signed by the user's wallet
            # For demo purposes, using fund wallet
            signed_txn = self.web3.eth.account.sign_transaction(
                transaction, 
                private_key=settings.FUND_PRIVATE_KEY
            )
            
            tx_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
            
            return TransactionResult(
                success=receipt.status == 1,
                transaction_hash=tx_hash.hex(),
                block_number=receipt.blockNumber,
                gas_used=receipt.gasUsed
            )
            
        except Exception as e:
            logger.error(f"Error creating proposal: {str(e)}")
            return TransactionResult(
                success=False,
                transaction_hash="",
                error_message=str(e)
            )
    
    async def cast_vote(
        self,
        voter_address: str,
        proposal_id: int,
        option: int,
        voting_power: float
    ) -> TransactionResult:
        """Cast a vote on a proposal"""
        try:
            if not self.proposal_manager_contract:
                self.proposal_manager_contract = self.load_contract('proposal_manager')
            
            # Convert voting power to wei
            voting_power_wei = int(voting_power * (10 ** 18))
            
            # Build transaction
            transaction = self.proposal_manager_contract.functions.vote(
                proposal_id,
                option,
                voting_power_wei
            ).build_transaction({
                'chainId': self.chain_id,
                'gas': 150000,
                'gasPrice': self.web3.to_wei('20', 'gwei'),
                'nonce': self.web3.eth.get_transaction_count(voter_address),
            })
            
            # Note: In production, signed by user's wallet
            signed_txn = self.web3.eth.account.sign_transaction(
                transaction, 
                private_key=settings.FUND_PRIVATE_KEY
            )
            
            tx_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
            
            return TransactionResult(
                success=receipt.status == 1,
                transaction_hash=tx_hash.hex(),
                block_number=receipt.blockNumber,
                gas_used=receipt.gasUsed
            )
            
        except Exception as e:
            logger.error(f"Error casting vote: {str(e)}")
            return TransactionResult(
                success=False,
                transaction_hash="",
                error_message=str(e)
            )
    
    async def get_proposal_results(self, proposal_id: int) -> Dict[str, Any]:
        """Get voting results for a proposal"""
        try:
            if not self.proposal_manager_contract:
                self.proposal_manager_contract = self.load_contract('proposal_manager')
            
            results = self.proposal_manager_contract.functions.getProposalResults(
                proposal_id
            ).call()
            
            return {
                'winning_option': results[0],
                'total_votes': results[1],
                'is_executed': results[2],
                'proposal_id': proposal_id
            }
            
        except Exception as e:
            logger.error(f"Error getting proposal results: {str(e)}")
            return {}
    
    async def create_sip_plan(
        self,
        user_address: str,
        amount_per_installment: float,
        frequency_days: int,
        duration_months: int
    ) -> TransactionResult:
        """Create a new SIP plan on blockchain"""
        try:
            if not self.sip_manager_contract:
                self.sip_manager_contract = self.load_contract('sip_manager')
            
            amount_wei = int(amount_per_installment * (10 ** 18))
            frequency_seconds = frequency_days * 24 * 3600
            duration_seconds = duration_months * 30 * 24 * 3600
            
            transaction = self.sip_manager_contract.functions.createSIP(
                amount_wei,
                frequency_seconds,
                duration_seconds
            ).build_transaction({
                'chainId': self.chain_id,
                'gas': 150000,
                'gasPrice': self.web3.to_wei('20', 'gwei'),
                'nonce': self.web3.eth.get_transaction_count(user_address),
            })
            
            signed_txn = self.web3.eth.account.sign_transaction(
                transaction, 
                private_key=settings.FUND_PRIVATE_KEY
            )
            
            tx_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
            
            return TransactionResult(
                success=receipt.status == 1,
                transaction_hash=tx_hash.hex(),
                block_number=receipt.blockNumber,
                gas_used=receipt.gasUsed
            )
            
        except Exception as e:
            logger.error(f"Error creating SIP plan: {str(e)}")
            return TransactionResult(
                success=False,
                transaction_hash="",
                error_message=str(e)
            )
    
    async def process_sip_payment(self, sip_id: int) -> TransactionResult:
        """Process a SIP payment"""
        try:
            if not self.sip_manager_contract:
                self.sip_manager_contract = self.load_contract('sip_manager')
            
            transaction = self.sip_manager_contract.functions.processSIPPayment(
                sip_id
            ).build_transaction({
                'chainId': self.chain_id,
                'gas': 200000,
                'gasPrice': self.web3.to_wei('20', 'gwei'),
                'nonce': self.web3.eth.get_transaction_count(settings.FUND_WALLET_ADDRESS),
            })
            
            signed_txn = self.web3.eth.account.sign_transaction(
                transaction, 
                private_key=settings.FUND_PRIVATE_KEY
            )
            
            tx_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
            
            return TransactionResult(
                success=receipt.status == 1,
                transaction_hash=tx_hash.hex(),
                block_number=receipt.blockNumber,
                gas_used=receipt.gasUsed
            )
            
        except Exception as e:
            logger.error(f"Error processing SIP payment: {str(e)}")
            return TransactionResult(
                success=False,
                transaction_hash="",
                error_message=str(e)
            )
    
    async def get_gas_price(self, strategy: str = "medium") -> int:
        """Get current gas price based on strategy"""
        try:
            # Get gas price from network
            current_gas_price = self.web3.eth.gas_price
            
            # Apply strategy multipliers
            multipliers = {
                "slow": 0.8,
                "medium": 1.0,
                "fast": 1.2,
                "fastest": 1.5
            }
            
            multiplier = multipliers.get(strategy, 1.0)
            return int(current_gas_price * multiplier)
            
        except Exception as e:
            logger.error(f"Error getting gas price: {str(e)}")
            return self.web3.to_wei('20', 'gwei')  # Default fallback
    
    async def estimate_gas(self, transaction: Dict) -> int:
        """Estimate gas required for a transaction"""
        try:
            gas_estimate = self.web3.eth.estimate_gas(transaction)
            # Add 20% buffer for safety
            return int(gas_estimate * 1.2)
        except Exception as e:
            logger.error(f"Error estimating gas: {str(e)}")
            return 200000  # Default fallback
    
    async def get_transaction_receipt(self, tx_hash: str) -> Optional[Dict]:
        """Get transaction receipt by hash"""
        try:
            receipt = self.web3.eth.get_transaction_receipt(tx_hash)
            return {
                'transaction_hash': receipt.transactionHash.hex(),
                'block_number': receipt.blockNumber,
                'gas_used': receipt.gasUsed,
                'status': receipt.status,
                'from': receipt['from'],
                'to': receipt.to,
                'contract_address': receipt.contractAddress
            }
        except TransactionNotFound:
            return None
        except Exception as e:
            logger.error(f"Error getting transaction receipt: {str(e)}")
            return None
    
    async def wait_for_transaction(self, tx_hash: str, timeout: int = 120) -> Optional[Dict]:
        """Wait for transaction to be mined"""
        try:
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)
            return await self.get_transaction_receipt(tx_hash)
        except Exception as e:
            logger.error(f"Error waiting for transaction: {str(e)}")
            return None
    
    async def get_block_timestamp(self, block_number: int) -> datetime:
        """Get timestamp of a specific block"""
        try:
            block = self.web3.eth.get_block(block_number)
            return datetime.fromtimestamp(block.timestamp)
        except Exception as e:
            logger.error(f"Error getting block timestamp: {str(e)}")
            return datetime.utcnow()
    
    async def get_contract_events(
        self,
        contract_name: str,
        event_name: str,
        from_block: int = 0,
        to_block: str = "latest"
    ) -> List[Dict]:
        """Get events from a smart contract"""
        try:
            contract = self.load_contract(contract_name)
            event_filter = getattr(contract.events, event_name).create_filter(
                fromBlock=from_block,
                toBlock=to_block
            )
            
            events = event_filter.get_all_entries()
            return [dict(event) for event in events]
            
        except Exception as e:
            logger.error(f"Error getting contract events: {str(e)}")
            return []
    
    async def encode_function_data(self, contract_name: str, function_name: str, *args) -> str:
        """Encode function call data"""
        try:
            contract = self.load_contract(contract_name)
            function = getattr(contract.functions, function_name)
            return function(*args).build_transaction({'gas': 0, 'gasPrice': 0})['data']
        except Exception as e:
            logger.error(f"Error encoding function data: {str(e)}")
            return "0x"
    
    async def verify_signature(self, message: str, signature: str, address: str) -> bool:
        """Verify a digital signature"""
        try:
            message_hash = self.web3.keccak(text=message)
            recovered_address = Account.recover_message(
                message_hash, 
                signature=signature
            )
            return recovered_address.lower() == address.lower()
        except Exception as e:
            logger.error(f"Error verifying signature: {str(e)}")
            return False
    
    # Multi-signature wallet operations
    async def create_multisig_transaction(
        self,
        multisig_address: str,
        to_address: str,
        value: int,
        data: str = "0x"
    ) -> Dict:
        """Create a multi-signature transaction proposal"""
        try:
            # This would interact with a multisig contract
            # For now, return a mock structure
            return {
                'transaction_id': 1,
                'to': to_address,
                'value': value,
                'data': data,
                'executed': False,
                'confirmations': 0,
                'required_confirmations': 3
            }
        except Exception as e:
            logger.error(f"Error creating multisig transaction: {str(e)}")
            return {}
    
    async def confirm_multisig_transaction(
        self,
        multisig_address: str,
        transaction_id: int,
        confirmer_address: str
    ) -> TransactionResult:
        """Confirm a multi-signature transaction"""
        try:
            # Mock implementation for demo
            return TransactionResult(
                success=True,
                transaction_hash="0x" + "a" * 64,
                block_number=12345678
            )
        except Exception as e:
            logger.error(f"Error confirming multisig transaction: {str(e)}")
            return TransactionResult(
                success=False,
                transaction_hash="",
                error_message=str(e)
            )
    
    # Price oracle integration
    async def get_asset_price_from_oracle(self, asset_symbol: str) -> Optional[float]:
        """Get asset price from on-chain price oracle"""
        try:
            # Integration with Chainlink or other price oracles
            # For demo, using external API
            response = requests.get(
                f"https://api.coingecko.com/api/v3/simple/price",
                params={
                    'ids': asset_symbol.lower(),
                    'vs_currencies': 'usd'
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get(asset_symbol.lower(), {}).get('usd')
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting price from oracle: {str(e)}")
            return None
    
    # Token swap operations (DEX integration)
    async def execute_token_swap(
        self,
        from_token: str,
        to_token: str,
        amount: float,
        slippage_tolerance: float = 0.01
    ) -> TransactionResult:
        """Execute token swap on DEX"""
        try:
            # Integration with Uniswap, PancakeSwap, etc.
            # For demo, return mock transaction
            return TransactionResult(
                success=True,
                transaction_hash="0x" + "b" * 64,
                block_number=12345679,
                gas_used=180000
            )
        except Exception as e:
            logger.error(f"Error executing token swap: {str(e)}")
            return TransactionResult(
                success=False,
                transaction_hash="",
                error_message=str(e)
            )
    
    # Staking operations
    async def stake_tokens(
        self,
        staker_address: str,
        amount: float,
        duration_days: int
    ) -> TransactionResult:
        """Stake governance tokens for additional rewards"""
        try:
            # Staking contract interaction
            amount_wei = int(amount * (10 ** 18))
            duration_seconds = duration_days * 24 * 3600
            
            # Mock transaction for demo
            return TransactionResult(
                success=True,
                transaction_hash="0x" + "c" * 64,
                block_number=12345680,
                gas_used=120000
            )
        except Exception as e:
            logger.error(f"Error staking tokens: {str(e)}")
            return TransactionResult(
                success=False,
                transaction_hash="",
                error_message=str(e)
            )
    
    async def unstake_tokens(self, staker_address: str, stake_id: int) -> TransactionResult:
        """Unstake tokens and claim rewards"""
        try:
            # Mock transaction for demo
            return TransactionResult(
                success=True,
                transaction_hash="0x" + "d" * 64,
                block_number=12345681,
                gas_used=140000
            )
        except Exception as e:
            logger.error(f"Error unstaking tokens: {str(e)}")
            return TransactionResult(
                success=False,
                transaction_hash="",
                error_message=str(e)
            )
    
    # Cross-chain operations
    async def bridge_tokens(
        self,
        from_chain: str,
        to_chain: str,
        token_address: str,
        amount: float,
        recipient_address: str
    ) -> TransactionResult:
        """Bridge tokens between different blockchains"""
        try:
            # Integration with cross-chain bridges
            # For demo, return mock transaction
            return TransactionResult(
                success=True,
                transaction_hash="0x" + "e" * 64,
                block_number=12345682,
                gas_used=250000
            )
        except Exception as e:
            logger.error(f"Error bridging tokens: {str(e)}")
            return TransactionResult(
                success=False,
                transaction_hash="",
                error_message=str(e)
            )
    
    # Governance utilities
    async def delegate_voting_power(
        self,
        delegator_address: str,
        delegate_address: str,
        amount: float
    ) -> TransactionResult:
        """Delegate voting power to another address"""
        try:
            amount_wei = int(amount * (10 ** 18))
            
            # Mock transaction for demo
            return TransactionResult(
                success=True,
                transaction_hash="0x" + "f" * 64,
                block_number=12345683,
                gas_used=100000
            )
        except Exception as e:
            logger.error(f"Error delegating voting power: {str(e)}")
            return TransactionResult(
                success=False,
                transaction_hash="",
                error_message=str(e)
            )
    
    async def revoke_delegation(
        self,
        delegator_address: str,
        delegate_address: str
    ) -> TransactionResult:
        """Revoke previously delegated voting power"""
        try:
            # Mock transaction for demo
            return TransactionResult(
                success=True,
                transaction_hash="0x" + "1" * 64,
                block_number=12345684,
                gas_used=80000
            )
        except Exception as e:
            logger.error(f"Error revoking delegation: {str(e)}")
            return TransactionResult(
                success=False,
                transaction_hash="",
                error_message=str(e)
            )
    
    # Utility functions
    def to_checksum_address(self, address: str) -> str:
        """Convert address to checksum format"""
        return Web3.to_checksum_address(address)
    
    def is_valid_address(self, address: str) -> bool:
        """Check if address is valid Ethereum address"""
        return Web3.is_address(address)
    
    def wei_to_eth(self, wei_amount: int) -> float:
        """Convert wei to ether"""
        return float(self.web3.from_wei(wei_amount, 'ether'))
    
    def eth_to_wei(self, eth_amount: float) -> int:
        """Convert ether to wei"""
        return self.web3.to_wei(eth_amount, 'ether')
    
    def generate_wallet(self) -> Tuple[str, str]:
        """Generate new wallet address and private key"""
        account = Account.create()
        return account.address, account.private_key.hex()
    
    async def get_network_info(self) -> Dict[str, Any]:
        """Get current network information"""
        try:
            latest_block = self.web3.eth.get_block('latest')
            gas_price = self.web3.eth.gas_price
            
            return {
                'chain_id': self.chain_id,
                'latest_block': latest_block.number,
                'block_timestamp': latest_block.timestamp,
                'gas_price_gwei': self.web3.from_wei(gas_price, 'gwei'),
                'is_connected': self.is_connected()
            }
        except Exception as e:
            logger.error(f"Error getting network info: {str(e)}")
            return {}