from sqlalchemy import text
import asyncio
from config import Config

from db import async_session

from web3 import Web3

async def main():
    config = Config()

    async with async_session() as session:
        result = await session.execute(
            text(
                """

                SELECT 
                    SUM(CASE WHEN to_address = :wallet THEN amount ELSE 0 END) -
                    SUM(CASE WHEN from_address = :wallet THEN amount ELSE 0 END) AS usdc_balance
                FROM token_transfers
                WHERE token_type = 'ERC20' AND LOWER(contract_address) = :usdc

                """
            ),
            {"wallet": config.my_wallet, "usdc": config.usdc}
        )

        balance_by_usdc = result.scalar_one_or_none()

        result = await session.execute(
            text(
                """

                SELECT 
                    token_id,
                    SUM(CASE WHEN to_address = :wallet THEN amount ELSE 0 END) -
                    SUM(CASE WHEN from_address = :wallet THEN amount ELSE 0 END) AS net_balance
                FROM token_transfers
                WHERE token_type = 'ERC1155'
                GROUP BY token_id

                """
            ),
            {"wallet": config.my_wallet}
        )

        balance_by_ctf = result.mappings().all()

        result = await session.execute(
            text(
                """
                SELECT last_scanned_block
                FROM progress
                WHERE contract_address = :wallet
                """
            ),
            {"wallet": config.my_wallet}
        )
        last_block = result.scalar_one_or_none()

        balance_c_sorted = []

        for c in balance_by_ctf:
            if c['net_balance'] != 0:
                balance_c_sorted.append(c)
        print('='*50)
        print("Итоговый баланс:")
        print(f"USDC: {balance_by_usdc}")
        print(f"Первые 20 CTF: {balance_c_sorted[0:20]}")
        print('='*50)
        w3 = Web3(Web3.HTTPProvider(config.rpc_url, request_kwargs={'timeout': config.rpc_timeout_seconds}))

        usdc_contract = w3.eth.contract(address=Web3.to_checksum_address(config.usdc), abi=config.ERC20_ABI)
        t_balance_usdc = usdc_contract.functions.balanceOf(Web3.to_checksum_address(config.my_wallet)).call(block_identifier=last_block)

        usdc_errors = 0
        ctf_errors = 0
        
        if t_balance_usdc == balance_by_usdc:
            print("USDC совпал")
            print(f'{t_balance_usdc} | {balance_by_usdc}')
        else:
            print("USDC не совпал")
            print(f'{t_balance_usdc} | {balance_by_usdc}')
            usdc_errors += 1

        ctf_contract = w3.eth.contract(address=Web3.to_checksum_address(config.ctf), abi=config.ERC1155_ABI)
        
        for b in balance_c_sorted:
            token_id = int(b['token_id'])
            t_balance_ctf = ctf_contract.functions.balanceOf(Web3.to_checksum_address(config.my_wallet), token_id).call(block_identifier=last_block)

            if t_balance_ctf == b['net_balance']:
                print("CTF совпал")
                print(f'{t_balance_ctf} | {b["net_balance"]}')
            else:
                print("CTF не совпал")
                print(f'{t_balance_ctf} | {b["net_balance"]}')
                ctf_errors += 1

        print('='*50)
        print('Проверка баланаса закончена')
        if usdc_errors == 0 and ctf_errors == 0:
            print("Баланс совпал")
        else:
            print("Баланс не совпал")
        print(f"USDC ошибки: {usdc_errors}")
        print(f"CTF ошибки: {ctf_errors}")

if __name__ == "__main__":
    asyncio.run(main())