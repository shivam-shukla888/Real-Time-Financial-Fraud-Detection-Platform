"""
Data Acquisition & Synthetic Generation Script.
Generates a realistic, reproducible, class-imbalanced financial transaction dataset
with embedded fraud rings, velocity bursts, and behavioral anomalies.
Clearly marked as synthetic for educational/capstone purposes.
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

# Ensure configs can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from configs.settings import settings, DATA_DIR


def generate_synthetic_transactions(
    n_records: int = 6000,
    fraud_rate: float = 0.022,
    seed: int = 42,
    output_path: Path = settings.DATA_PATH,
) -> pd.DataFrame:
    """
    Generates a deterministic synthetic transactions dataset with realistic financial patterns.
    Embeds fraud rings (shared devices/accounts) and velocity bursts.
    """
    np.random.seed(seed)
    print(f"[*] Generating {n_records} synthetic transactions (seed={seed}, target fraud rate={fraud_rate:.1%})...")

    start_date = datetime(2026, 10, 1, 0, 0, 0)

    # Base entity pools
    n_legit_accounts = 350
    n_legit_devices = 420
    n_legit_merchants = 80

    accounts = [f"ACC_{1000 + i}" for i in range(n_legit_accounts)]
    devices = [f"DEV_{2000 + i}" for i in range(n_legit_devices)]
    merchants = [f"MERCH_{3000 + i}" for i in range(n_legit_merchants)]

    categories = [
        "groceries", "electronics", "online_retail", "travel", 
        "dining", "entertainment", "money_transfer", "crypto_exchange"
    ]
    category_weights = [0.28, 0.12, 0.22, 0.08, 0.16, 0.07, 0.05, 0.02]

    locations = [
        "New York, US", "San Francisco, US", "Chicago, US", "Austin, US",
        "London, UK", "Toronto, CA", "Berlin, DE", "Tokyo, JP", "Sydney, AU"
    ]
    payment_methods = ["credit_card", "debit_card", "ach_transfer", "mobile_wallet"]

    # Assign primary device and home location to legit accounts
    account_primary_device = {acc: np.random.choice(devices) for acc in accounts}
    account_home_location = {acc: np.random.choice(locations, p=[0.35, 0.20, 0.15, 0.10, 0.05, 0.05, 0.04, 0.03, 0.03]) for acc in accounts}

    # Pre-generate timestamps chronologically across 14 days
    time_deltas = np.sort(np.random.exponential(scale=200, size=n_records))  # average 200 sec between transactions
    timestamps = [start_date + timedelta(seconds=int(td)) for td in np.cumsum(time_deltas)]

    # Prepare lists
    records = []

    # Fraud ring definitions (for Phase D graph analysis)
    fraud_ring_1_accounts = [f"ACC_RING1_{i}" for i in range(1, 6)]
    fraud_ring_1_devices = ["DEV_RING1_A", "DEV_RING1_B"]
    fraud_ring_1_merchant = "MERCH_MULE_CORP"

    fraud_ring_2_accounts = [f"ACC_RING2_{i}" for i in range(1, 5)]
    fraud_ring_2_device = "DEV_RING2_EMULATOR"
    fraud_ring_2_merchant = "MERCH_CRYPTO_SWAP"

    # Pre-determine which transactions will be fraud ring events
    n_ring_events = int(n_records * 0.012)
    ring_indices = set(np.random.choice(range(n_records // 3, n_records), size=n_ring_events, replace=False))

    # Pre-determine individual opportunistic fraud transactions
    n_individual_fraud = int(n_records * (fraud_rate - 0.012))
    eligible_fraud_indices = set(range(n_records)) - ring_indices
    individual_fraud_indices = set(np.random.choice(list(eligible_fraud_indices), size=n_individual_fraud, replace=False))

    for i in range(n_records):
        txn_id = f"TXN_{100000 + i}"
        ts = timestamps[i]

        if i in ring_indices:
            # Belongs to a fraud ring cluster
            ring_id = 1 if np.random.rand() > 0.45 else 2
            if ring_id == 1:
                account = np.random.choice(fraud_ring_1_accounts)
                device = np.random.choice(fraud_ring_1_devices)
                merchant = fraud_ring_1_merchant
                category = "money_transfer"
                amount = float(np.random.uniform(900.0, 3500.0))
                location = "Unknown / Proxy IP"
                payment = "ach_transfer"
            else:
                account = np.random.choice(fraud_ring_2_accounts)
                device = fraud_ring_2_device
                merchant = fraud_ring_2_merchant
                category = "crypto_exchange"
                amount = float(np.random.uniform(1200.0, 4800.0))
                location = "Offshore Hosting Node"
                payment = "credit_card"
            is_fraud = 1

        elif i in individual_fraud_indices:
            # Individual fraud pattern (account takeover / stolen card / rapid velocity)
            account = np.random.choice(accounts)
            # 85% chance of unusual/new device
            device = f"DEV_ROGUE_{np.random.randint(9000, 9999)}" if np.random.rand() < 0.85 else account_primary_device[account]
            merchant = np.random.choice(merchants)
            category = np.random.choice(["electronics", "luxury", "crypto_exchange", "travel"])
            # Unusually large amount
            amount = float(np.random.exponential(scale=650) + 400.0)
            location = np.random.choice(["Lagos, NG", "Bucharest, RO", "Eastern Europe Node", "Unknown / Proxy IP"])
            payment = np.random.choice(payment_methods)
            is_fraud = 1

        else:
            # Legitimate financial transaction
            account = np.random.choice(accounts)
            # 94% of the time, uses legitimate primary device
            if np.random.rand() < 0.94:
                device = account_primary_device[account]
            else:
                device = np.random.choice(devices)  # Secondary device (e.g. tablet, work laptop)

            merchant = np.random.choice(merchants)
            category = np.random.choice(categories, p=category_weights)
            
            # Realistic log-normal amount by category
            if category == "groceries":
                amount = float(np.random.lognormal(mean=3.8, sigma=0.6))  # ~$50
            elif category == "dining":
                amount = float(np.random.lognormal(mean=3.5, sigma=0.5))  # ~$38
            elif category == "electronics":
                amount = float(np.random.lognormal(mean=5.2, sigma=0.8))  # ~$220
            elif category == "travel":
                amount = float(np.random.lognormal(mean=5.8, sigma=0.7))  # ~$380
            else:
                amount = float(np.random.lognormal(mean=4.1, sigma=0.7))  # ~$70

            # Usually home location
            if np.random.rand() < 0.95:
                location = account_home_location[account]
            else:
                location = np.random.choice(locations)  # travel
            
            payment = np.random.choice(payment_methods, p=[0.55, 0.30, 0.10, 0.05])
            is_fraud = 0

        records.append({
            "transaction_id": txn_id,
            "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "account_id": account,
            "merchant_id": merchant,
            "category": category,
            "amount": round(amount, 2),
            "device_id": device,
            "location": location,
            "payment_method": payment,
            "is_fraud": is_fraud,
            "is_synthetic": 1  # Mandatory transparency flag
        })

    df = pd.DataFrame(records)
    # Ensure chronological order
    df = df.sort_values(by="timestamp").reset_index(drop=True)

    # Save to CSV
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)

    fraud_count = df["is_fraud"].sum()
    print(f"[OK] Successfully generated and saved {len(df)} transactions to: {output_path}")
    print(f"[INFO] Legit: {len(df) - fraud_count} | Fraud: {fraud_count} ({fraud_count/len(df):.2%})")
    print(f"[INFO] Unique Accounts: {df['account_id'].nunique()} | Unique Devices: {df['device_id'].nunique()}")

    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic fraud transaction dataset.")
    parser.add_argument("--count", type=int, default=6000, help="Number of transaction records to generate.")
    parser.add_argument("--seed", type=int, default=settings.RANDOM_SEED, help="Random seed for reproducibility.")
    args = parser.parse_args()

    generate_synthetic_transactions(n_records=args.count, seed=args.seed)
