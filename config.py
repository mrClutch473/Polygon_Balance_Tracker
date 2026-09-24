import os

from dotenv import load_dotenv
import hashlib

class Config():

    def __init__(self):

        load_dotenv()

        self.my_wallet = os.getenv('WALLET').lower()
        self.rpc_url = os.getenv('RPC')
        self.rpc_url_backup = os.getenv('RPC_BACKUP')
        self.usdc = os.getenv('USDC').lower()
        self.ctf = os.getenv('CTF').lower()

        self.transfer_erc20 = os.getenv('TRANSFER_ERC20')
        self.transfer_single1155 = os.getenv('TRANSFER_SINGLE1155')
        self.transfer_batch1155 = os.getenv('TRANSFER_BATCH1155')

        self.n = int(os.getenv('ITERATIONS'))
        self.max_retries = int(os.getenv('MAX_RETRIES'))
        self.delay_retries = int(os.getenv('DELAY_RETRIES'))

        self.postgres_user = os.getenv('POSTGRES_USER')
        self.postgres_password = os.getenv('POSTGRES_PASSWORD')
        self.postgres_db = os.getenv('POSTGRES_DB')

        self.database_url = os.getenv('DATABASE_URL')

        self.start_block = int(os.getenv('START_BLOCK'))

        self.log_rpc_urls = (
            "https://gateway.tenderly.co/public/polygon",
            "https://polygon.gateway.tenderly.co",
            "https://polygon-bor-mainnet.rpc.services.stakecraft.com",
        )

        self.call_rpc_urls = (
            "https://gateway.tenderly.co/public/polygon",
            "https://polygon.gateway.tenderly.co",
            "https://rpc-mainnet.matic.quiknode.pro",
            "https://polygon.drpc.org",
            "https://polygon.rpc.thirdweb.com",
            "https://rpc.decentraland.org/polygon",
        )

        self.rpc_timeout_seconds = int(os.getenv('RPC_TIMEOUT_SECONDS'))

        self.ERC20_ABI = [
            {
                "constant": True,
                "inputs": [{"name": "account", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            }
        ]

        self.ERC1155_ABI = [
            {
                "constant": True,
                "inputs": [
                    {"name": "account", "type": "address"},
                    {"name": "id", "type": "uint256"}
                ],
                "name": "balanceOf",
                "outputs": [{"name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            }
        ]

        self.ERC1155_BATCH_ABI = [
            {
                "constant": True,
                "inputs": [
                    {"name": "accounts", "type": "address[]"},
                    {"name": "ids", "type": "uint256[]"}
                ],
                "name": "balanceOfBatch",
                "outputs": [{"name": "", "type": "uint256[]"}],
                "stateMutability": "view",
                "type": "function"
            }
        ]

    def get_wallet_topic(self) -> str:
        return '0x' + self.my_wallet[2:].zfill(64)

    def get_contracts_hash(self) -> str:
        contracts_raw = [self.usdc, self.ctf]
        contracts_str = ''.join(sorted(contracts_raw))
        return hashlib.sha256(contracts_str.encode()).hexdigest()