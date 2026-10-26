# Dataset Card: Financial Fraud Transactions

## 1. Dataset Overview

- **Dataset Identifier**: `sample_transactions.csv`
- **Dataset Version**: 1.0.0
- **Creation Date**: October 2026
- **Provenance**: Deterministic synthetic generation via `scripts/prepare_data.py` (Random Seed 42).
- **Domain**: Retail banking, card-not-present e-commerce, and instant account-to-account (A2A) transfers.
- **License**: MIT (Educational Capstone Use).
- **Synthetic Disclaimer**: **All entities, account numbers, device hashes, and transaction amounts are entirely simulated.** This dataset does not contain real customer data, real banking credentials, or live card numbers.

---

## 2. Dataset Composition & Statistics

| Characteristic | Measurement |
| :--- | :--- |
| **Total Record Count** | 6,000 transactions |
| **Total File Size** | 0.63 MB (well below the 25 MB safety limit) |
| **Chronological Span** | 2026-10-01 00:00:00 to 2026-10-14 17:18:50 (14 days) |
| **Legitimate Transactions (0)** | 5,869 (97.82%) |
| **Fraudulent Transactions (1)** | 131 (2.18%) |
| **Class Imbalance Ratio** | ~44.8 : 1 (Negative : Positive) |
| **Unique Accounts** | 359 |
| **Unique Devices** | 385 |
| **Unique Merchants** | 82 |

---

## 3. Schema & Field Definitions

| Column | Type | Nullable | Description |
| :--- | :--- | :--- | :--- |
| `transaction_id` | String | No | Unique transaction identifier (`TXN_100000` to `TXN_105999`). |
| `timestamp` | Datetime (ISO) | No | Monotonically increasing event timestamp. |
| `account_id` | String | No | Originating customer account ID (`ACC_1000` to `ACC_1349`, or `ACC_RING*`). |
| `merchant_id` | String | No | Terminal / destination merchant ID. |
| `category` | String | No | Spending category (e.g. `groceries`, `electronics`, `money_transfer`). |
| `amount` | Float | No | Transaction amount in USD ($5.51 to $5,352.12). |
| `device_id` | String | No | Synthetic client device / browser fingerprint. |
| `location` | String | No | IP geographic origin node. |
| `payment_method` | String | No | Payment rail (`credit_card`, `debit_card`, `ach_transfer`, `mobile_wallet`). |
| `is_fraud` | Integer (0/1) | No | Ground truth fraud label. |
| `is_synthetic` | Integer (1) | No | Mandatory transparency flag marking simulated data. |

---

## 4. Seeded Fraud Typologies

To benchmark both supervised tabular models and graph syndicate algorithms, three distinct fraud archetypes are embedded:

1. **Velocity Spikes & Account Takeover (ATO)**:
   - Legitimate accounts suddenly initiating high-amount transactions from new devices or foreign IP locations (e.g., Eastern Europe / Lagos nodes).
2. **Mule Syndicate Ring #1**:
   - 5 synthetic accounts (`ACC_RING1_1` to `ACC_RING1_5`) sharing 2 high-velocity devices (`DEV_RING1_A`, `DEV_RING1_B`) routing large wire transfers into `MERCH_MULE_CORP`.
3. **Emulator / Bot Farm #2**:
   - 4 accounts originating from a single virtual device (`DEV_RING2_EMULATOR`) executing burst payments into `MERCH_CRYPTO_SWAP`.

---

## 5. Instructions for Integrating Real-World Benchmarks

To replace this synthetic dataset with an authorized benchmark (e.g., PaySim or ULB Credit Card Fraud):
1. Download an authorized subset (< 25 MB).
2. Rename/map fields to the standard schema above.
3. Validate schema compliance:
   ```powershell
   python scripts/verify_data.py
   ```
4. Retrain the model:
   ```powershell
   python scripts/train_model.py
   ```
