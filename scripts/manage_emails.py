import asyncio
import sys
import argparse
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from src.services.database import db
from src.config import settings

async def list_emails():
    """List all custom email recipients."""
    print("Fetching custom email recipients...")
    async with db.get_connection() as conn:
        cursor = await conn.execute(
            "SELECT value FROM preferences WHERE key = 'DELIVERY_EMAIL_CUSTOM_RECIPIENTS'"
        )
        row = await cursor.fetchone()
        
    if row and row[0]:
        emails = [e.strip() for e in row[0].split(',') if e.strip()]
        if emails:
            print("\nRegistered Custom Recipients:")
            for i, email in enumerate(emails, 1):
                print(f"{i}. {email}")
        else:
            print("\nNo custom recipients found.")
    else:
        print("\nNo custom recipients found.")

async def add_email(email: str):
    """Add a new email to the list."""
    if not email or '@' not in email:
        print("Error: Invalid email address")
        return

    async with db.get_connection() as conn:
        # Get existing
        cursor = await conn.execute(
            "SELECT value FROM preferences WHERE key = 'DELIVERY_EMAIL_CUSTOM_RECIPIENTS'"
        )
        row = await cursor.fetchone()
        current_val = row[0] if row else ""
        
        current_emails = [e.strip() for e in current_val.split(',') if e.strip()]
        
        if email in current_emails:
            print(f"Email '{email}' is already in the list.")
            return
            
        current_emails.append(email)
        new_val = ",".join(current_emails)
        
        await conn.execute(
            "INSERT OR REPLACE INTO preferences (key, value) VALUES (?, ?)",
            ('DELIVERY_EMAIL_CUSTOM_RECIPIENTS', new_val)
        )
        await conn.commit()
        print(f"Successfully added '{email}'.")

async def remove_email(email: str):
    """Remove an email from the list."""
    async with db.get_connection() as conn:
        cursor = await conn.execute(
            "SELECT value FROM preferences WHERE key = 'DELIVERY_EMAIL_CUSTOM_RECIPIENTS'"
        )
        row = await cursor.fetchone()
        current_val = row[0] if row else ""
        
        current_emails = [e.strip() for e in current_val.split(',') if e.strip()]
        
        if email not in current_emails:
            print(f"Email '{email}' not found in the list.")
            return
            
        current_emails.remove(email)
        new_val = ",".join(current_emails)
        
        await conn.execute(
            "INSERT OR REPLACE INTO preferences (key, value) VALUES (?, ?)",
            ('DELIVERY_EMAIL_CUSTOM_RECIPIENTS', new_val)
        )
        await conn.commit()
        print(f"Successfully removed '{email}'.")

async def main():
    parser = argparse.ArgumentParser(description="Manage custom email recipients for AI Digest")
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # List command
    subparsers.add_parser('list', help='List all registered emails')
    
    # Add command
    add_parser = subparsers.add_parser('add', help='Add a new email')
    add_parser.add_argument('email', help='Email address to add')
    
    # Remove command
    remove_parser = subparsers.add_parser('remove', help='Remove an email')
    remove_parser.add_argument('email', help='Email address to remove')
    
    args = parser.parse_args()
    
    if args.command == 'list':
        await list_emails()
    elif args.command == 'add':
        await add_email(args.email)
    elif args.command == 'remove':
        await remove_email(args.email)
    else:
        parser.print_help()

if __name__ == "__main__":
    asyncio.run(main())
