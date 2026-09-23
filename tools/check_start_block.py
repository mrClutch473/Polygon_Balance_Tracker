from web3 import Web3
from config import Config

config = Config()
w3 = Web3(Web3.HTTPProvider(config.rpc_url))

wallet = w3.to_checksum_address(config.my_wallet)

t1 = 0
t2 = w3.eth.block_number

while t1 < t2:
    mid = (t1 + t2) // 2
    try:
        code = w3.eth.get_code(wallet, block_identifier=mid)
    except Exception:
        code = b''

    if code == b'':
        t1 = mid + 1
    else:
        t2 = mid

print(f"START_BLOCK: {t1}")