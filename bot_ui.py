import json
import requests
import sqlite3
from datetime import datetime

# Load configuration
with open("config.json") as config_file:
    config = json.load(config_file)

# Fetch token data from DexScreener
def fetch_token_data(token_address):
    response = requests.get(f"{config['dex_api_url']}{token_address}")
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to fetch data for token: {token_address}")
        return None

# Parse token data
def parse_token_data(token_data):
    pair_created_at = datetime.fromtimestamp(token_data["pairCreatedAt"] / 1000)
    token_age_days = (datetime.now() - pair_created_at).days

    parsed_data = {
        "token_address": token_data["address"],
        "price": token_data["price"],
        "volume": token_data["volume"],
        "liquidity": token_data["liquidity"],
        "market_cap": token_data["marketCap"],
        "pair_created_at": pair_created_at,
        "token_age_days": token_age_days,
        "developer_address": token_data.get("developerAddress", "unknown")
    }
    return parsed_data

# Check RugCheck status
def check_rugcheck_status(token_address):
    try:
        response = requests.get(f"{config['rugcheck_api_url']}/check?token={token_address}")
        if response.status_code == 200:
            data = response.json()
            return data.get("status", "Risky")
        else:
            print(f"Failed to fetch RugCheck data for token: {token_address}")
            return "Risky"
    except Exception as e:
        print(f"Error checking RugCheck status: {e}")
        return "Risky"

# Check supply bundling
def check_supply_bundling(token_data):
    liquidity = token_data["liquidity"]
    market_cap = token_data["market_cap"]
    if liquidity > 0 and (market_cap / liquidity) > 100:
        return True
    return False

# Update blacklist
def update_blacklist(token_address, developer_address):
    if token_address not in config["blacklist"]["tokens"]:
        config["blacklist"]["tokens"].append(token_address)
    if developer_address not in config["blacklist"]["developers"]:
        config["blacklist"]["developers"].append(developer_address)
    
    with open("config.json", "w") as config_file:
        json.dump(config, config_file, indent=4)

# Save to database
def save_to_db(data):
    conn = sqlite3.connect(config["database_name"])
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tokens (
            token_address TEXT PRIMARY KEY,
            price REAL,
            volume REAL,
            liquidity REAL,
            market_cap REAL,
            pair_created_at TEXT,
            developer_address TEXT
        )
    ''')
    cursor.execute('''
        INSERT OR REPLACE INTO tokens VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        data["token_address"], data["price"], data["volume"], data["liquidity"],
        data["market_cap"], data["pair_created_at"].isoformat(), data["developer_address"]
    ))
    conn.commit()
    conn.close()

# Main function
def main():
    token_address = "0xYourTokenAddressHere"
    token_data = fetch_token_data(token_address)
    
    if token_data:
        parsed_data = parse_token_data(token_data)
        
        # Check RugCheck status
        rugcheck_status = check_rugcheck_status(token_address)
        if rugcheck_status != "Good":
            print(f"Token {token_address} is not marked as 'Good' on RugCheck.")
            return
        
        # Check supply bundling
        if check_supply_bundling(parsed_data):
            print(f"Token {token_address} has bundled supply. Blacklisting token and developer.")
            update_blacklist(token_address, parsed_data["developer_address"])
            return
        
        # Save to database
        save_to_db(parsed_data)
        print(f"Token {token_address} saved to database.")
    else:
        print("Failed to process token data.")

if __name__ == "__main__":
    main()
