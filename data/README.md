# Data Documentation & Provenance

> **EDUCATIONAL DEMO NOTICE**: The dataset provided in this project (`data/sample_transactions.csv`) is a deterministic, synthetic transaction dataset generated specifically for this educational capstone. It contains NO real cardholder data, banking credentials, or personally identifiable information (PII). All results obtained from this data must not be construed as real-world banking fraud rates.

---

## 1. Overview & Dataset Profile

- **File Name**: `data/sample_transactions.csv`
- **File Size**: ~0.63 MB (strictly below the 25 MB safety limit)
- **Record Count**: 6,000 transactions
- **Time Span**: 2026-10-01 00:00:00 to 2026-10-14 17:18:50 (14 days)
- **Class Imbalance**:
  - Legitimate Transactions (`is_fraud = 0`): 5,869 (97.82%)
  - Fraudulent Transactions (`is_fraud = 1`): 131 (2.18%)
- **Entities**:
  - Unique Accounts: 359
  - Unique Devices: 385
  - Unique Merchants: 82

---

## 2. Schema Specification

| Field Name | Type | Description | Example |
| :--- | :--- | :--- | :--- |
| `transaction_id` | String | Unique transaction identifier | `TXN_100042` |
| `timestamp` | Datetime (ISO 8601) | Transaction timestamp (strictly monotonic) | `2026-10-01 14:22:10` |
| `account_id` | String | Synthetic account identifier | `ACC_1042` |
| `merchant_id` | String | Synthetic merchant identifier | `MERCH_3015` |
| `category` | String | Merchant / transaction category | `electronics`, `groceries`, `money_transfer` |
| `amount` | Float | Transaction amount in USD | `142.50` |
| `device_id` | String | Synthetic device / browser fingerprint | `DEV_2011` |
| `location` | String | Geographic IP / node location | `New York, US`, `Lagos, NG` |
| `payment_method` | String | Payment rail | `credit_card`, `ach_transfer`, `mobile_wallet` |
| `is_fraud` | Integer (0/1) | Ground-truth binary fraud label | `0` (legit), `1` (fraud) |
| `is_synthetic` | Integer (1) | Transparency flag denoting simulated data | `1` |

---

## 3. Embedded Fraud Rings & Typologies

To validate the multi-layer detection architecture (Supervised ML + Graph Analytics), realistic fraud typologies are seeded:

1. **Fraud Ring 1 — Mule Account Syndicate (`ACC_RING1_*`)**:
   - 5 accounts sharing 2 high-velocity devices (`DEV_RING1_A`, `DEV_RING1_B`).
   - Funnel high-velocity wire transfers through an illicit merchant entity (`MERCH_MULE_CORP`).
2. **Fraud Ring 2 — Emulator / Bot Farm (`ACC_RING2_*`)**:
   - 4 accounts originating from a single virtual emulator device (`DEV_RING2_EMULATOR`).
   - High-amount bursts into cryptocurrency swap channels (`MERCH_CRYPTO_SWAP`).
3. **Opportunistic Account Takeover (ATO) / Device Spoofing**:
   - Stolen credential bursts utilizing sudden new devices (`DEV_ROGUE_*`) and geographic anomalies.

---

## 4. Replacing with an Authorized Real Dataset

To swap this synthetic dataset with a real or benchmark fraud dataset (e.g., PaySim or ULB credit card fraud):

1. **Obtain an authorized sample**:
   - Ensure the sample is under 25 MB and complies with privacy / terms of service.
   - Example sources: Kaggle Credit Card Fraud Detection (284,807 transactions, anonymized PCA) or PaySim mobile money transfer sample.
2. **Normalize columns**: Map columns to the expected schema (`transaction_id`, `timestamp`, `account_id`, `amount`, `is_fraud`, etc.).
3. **Run Verification**:
   ```powershell
   python scripts/verify_data.py
   ```
4. **Retrain the Pipeline**:
   ```powershell
   python scripts/train_model.py
   ```
