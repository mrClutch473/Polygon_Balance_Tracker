import os

from web3 import Web3

from datetime import datetime, timezone
from eth_abi import decode as abi_decode
import asyncio

from sqlalchemy import select

from config import Config

from db import async_session
from models import TokenTransfers, Progress

from db import init_db

def get_topic(adress: str) -> str:
    topic = '0x' + adress[2:].zfill(64)
    return topic

def get_logs(w3: Web3, config: Config, start:int, end:int):

    erc20_out_filter = {
        "fromBlock": start,
        "toBlock": end,
        "address": w3.to_checksum_address(config.usdc),
        "topics": [config.transfer_erc20, config.get_wallet_topic()]
    }

    erc20_in_filter = {
        "fromBlock": start,
        "toBlock": end,
        "address": w3.to_checksum_address(config.usdc),
        "topics": [config.transfer_erc20, None, config.get_wallet_topic()]
    }

    single1155_out_filter = {
        "fromBlock": start,
        "toBlock": end,
        "address": w3.to_checksum_address(config.ctf),
        "topics": [config.transfer_single1155, None, config.get_wallet_topic()]
    }

    single1155_in_filter = {
        "fromBlock": start,
        "toBlock": end,
        "address": w3.to_checksum_address(config.ctf),
        "topics": [config.transfer_single1155, None, None, config.get_wallet_topic()]
    }

    batch1155_out_filter = {
        "fromBlock": start,
        "toBlock": end,
        "address": w3.to_checksum_address(config.ctf),
        "topics": [config.transfer_batch1155, None, config.get_wallet_topic()]
    }

    batch1155_in_filter = {
        "fromBlock": start,
        "toBlock": end,
        "address": w3.to_checksum_address(config.ctf),
        "topics": [config.transfer_batch1155,None, None, config.get_wallet_topic()]
    }

    all_logs = []
    all_logs.extend(make_smaller_range(w3, erc20_out_filter, start, end))
    all_logs.extend(make_smaller_range(w3, erc20_in_filter, start, end))
    all_logs.extend(make_smaller_range(w3, single1155_out_filter, start, end))
    all_logs.extend(make_smaller_range(w3, single1155_in_filter, start, end))
    all_logs.extend(make_smaller_range(w3, batch1155_out_filter, start, end))
    all_logs.extend(make_smaller_range(w3, batch1155_in_filter, start, end))

    temp = set()
    uniqe = []
    for log in all_logs:
        log_if = (log['blockNumber'], log['logIndex'])
        if log_if not in temp:
            temp.add(log_if)
            uniqe.append(log)

    unique_sorted = sorted(uniqe, key=lambda x: (x['blockNumber'], x['logIndex']))

    return unique_sorted

def make_smaller_range(w3: Web3, params:dict, start:int, end:int):
    params['fromBlock'] = start
    params['toBlock'] = end
    try:
        return w3.eth.get_logs(params)
    except Exception as e:
        if "returned more than" in str(e):
            mid = (start + end) // 2
            l = make_smaller_range(w3, params, start, mid)
            r = make_smaller_range(w3, params, mid + 1, end)
            return l + r
        else:
            raise

async def save_logs(logs: list, config: Config, end):

    async with async_session() as session:
        for log in logs:
            block_number = log['blockNumber']
            log_index = log['logIndex']
            transaction_hash = "0x" + log['transactionHash'].hex().removeprefix("0x")
            address = log['address']
            hash = "0x" + log['topics'][0].hex()

            
            if 'blockTimestamp' in log:
                block_ts = datetime.fromtimestamp(int(log['blockTimestamp'], 16), tz=timezone.utc).replace(tzinfo=None)
            else:
                block_ts = None
            
            if hash == config.transfer_erc20:
                from_addr = "0x" + log['topics'][1].hex()[-40:]
                to_addr = "0x" + log['topics'][2].hex()[-40:]
                amount = int(log['data'].hex(), 16)

                session.add(TokenTransfers(
                    block_number=block_number, log_index=log_index, batch_position=0,
                    tx_hash=transaction_hash, token_type="ERC20", contract_address=address,
                    token_id=0, from_address=from_addr, to_address=to_addr,
                    amount=amount, block_timestamp=block_ts,
                ))

            elif hash == config.transfer_single1155:
                from_addr = "0x" + log['topics'][2].hex()[-40:]
                to_addr = "0x" + log['topics'][3].hex()[-40:]

                data = bytes(log['data'])
                token_id = int.from_bytes(data[0:32], "big")
                amount = int.from_bytes(data[32:64], "big")

                session.add(TokenTransfers(
                    block_number=block_number, log_index=log_index, batch_position=0,
                    tx_hash=transaction_hash, token_type="ERC1155", contract_address=address,
                    token_id=token_id, from_address=from_addr, to_address=to_addr,
                    amount=amount, block_timestamp=block_ts,
                ))

            elif hash == config.transfer_batch1155:
                from_addr = "0x" + log['topics'][2].hex()[-40:]
                to_addr = "0x" + log['topics'][3].hex()[-40:]

                data = bytes(log['data'])
                ids, values = abi_decode(["uint256[]", "uint256[]"], data)

                for i, (token_id, amount) in enumerate(zip(ids, values)):
                    session.add(TokenTransfers(
                        block_number=block_number, log_index=log_index, batch_position=i,
                        tx_hash=transaction_hash, token_type="ERC1155", contract_address=address,
                        token_id=token_id, from_address=from_addr, to_address=to_addr,
                        amount=amount, block_timestamp=block_ts,
                    ))

        result = await session.execute(
            select(Progress).where(Progress.contract_address == config.my_wallet)
        )
        progress = result.scalar_one_or_none()

        if progress:
            progress.last_scanned_block = end
            progress.contracts_hash = config.get_contracts_hash()
        else:
            session.add(Progress(contract_address=config.my_wallet, last_scanned_block=end, contracts_hash=config.get_contracts_hash()))

        await session.commit()
        

async def main():
    await init_db()

    config = Config()

    w3_arr = []

    w3_1 = Web3(Web3.HTTPProvider(config.rpc_url, request_kwargs={'timeout': config.rpc_timeout_seconds}))
    w3_arr.append(w3_1)

    for url in config.log_rpc_urls:
        w3 = Web3(Web3.HTTPProvider(url, request_kwargs={'timeout': config.rpc_timeout_seconds}))
        if w3.is_connected():
            w3_arr.append(w3)

    print(w3_arr[0].eth.block_number)

    latest_block = w3_arr[0].eth.block_number
    
    print("Начало обработки")
    print()

    async with async_session() as session:
        result = await session.execute(
            select(Progress).where(Progress.contract_address == config.my_wallet)
        )
        progress = result.scalar_one_or_none()

    cur_hash = config.get_contracts_hash()

    if progress is None:
        current = config.start_block
    elif progress.contracts_hash != cur_hash:
        print("Изменились контракты, повторное сканирование")
        current = config.start_block
    else:
        current = progress.last_scanned_block + 1

    while current <= latest_block:
        end = min(current + config.n, latest_block)

        delay = config.delay_retries

        for i in range(config.max_retries):
            try:
                logs = get_logs(w3_arr[i % len(w3_arr)], config, current, end)
                await save_logs(logs, config, end)
                break
            except Exception as e:
                if i == config.max_retries-1:
                    print('Превышено количество ретраев')
                    raise
                print('Ошибка при получении логов:', e)
                await asyncio.sleep(delay)
                delay *= 2

        print(f"Обработаны: {current} - {end} | Всего: {latest_block} | Найдено логов: {len(logs)}")

        current = end + 1

    print()
    print("Конец обработки")


if __name__ == "__main__":
    asyncio.run(main())