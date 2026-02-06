import asyncio
import aiosmtplib
import socket

import ssl

async def check_port(host, port, use_ssl=False):
    print(f"Testing connectivity to {host}:{port} (SSL={use_ssl})...")
    try:
        if use_ssl:
            ctx = ssl.create_default_context()
            reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port, ssl=ctx), timeout=10.0)
        else:
            reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=10.0)
        print(f"[OK] Connection established to {host}:{port}")
        
        try:
            greeting = await asyncio.wait_for(reader.read(1024), timeout=5.0)
            print(f"[OK] Received greeting from {host}:{port}: {greeting.decode().strip()[:50]}...")
        except asyncio.TimeoutError:
            print(f"[FAIL] Timed out waiting for greeting from {host}:{port}")
        except Exception as e:
            print(f"[FAIL] Error reading greeting from {host}:{port}: {e}")
            
        writer.close()
        await writer.wait_closed()
    except asyncio.TimeoutError:
        print(f"[FAIL] Timed out connecting to {host}:{port}")
    except Exception as e:
        print(f"[FAIL] Failed to connect to {host}:{port}: {e}")

async def main():
    print("Starting SMTP Connectivity Test...")
    await check_port("smtp.gmail.com", 587, use_ssl=False)
    await check_port("smtp.gmail.com", 465, use_ssl=True)

if __name__ == "__main__":
    asyncio.run(main())
