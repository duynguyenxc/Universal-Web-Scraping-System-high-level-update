## Running UWSS on AWS EC2 and Uploading Results to S3

This guide shows **end‑to‑end steps** to:

- **Launch an EC2 instance** for running UWSS.
- **Set up the environment** (Python, virtualenv, repo, dependencies).
- **Run the UWSS pipeline** on EC2.
- **Upload all collected data** from EC2 to an **S3 bucket**.
****
It assumes you already have an **AWS account** and basic familiarity with the AWS Console.

---

## 1. Create and prepare an EC2 instance

### 1.1. Launch EC2 (Ubuntu)

In the AWS Console:

- **Service**: EC2 → *Launch instance*.
- **AMI**: `Ubuntu Server 24.04 LTS` (or similar).
- **Instance type**: at least `t3.medium` (2 vCPU, 4GB RAM) or larger for heavier runs.
- **Key pair**: create or select an existing `.pem` key (you will use this to SSH).
- **Network**:
  - Ensure the instance has a **public IP** if you SSH from the internet.
  - Security group: allow inbound **SSH (port 22)** from your IP.

### 1.2. Attach IAM role for S3 access (recommended)

To avoid embedding access keys on the instance:

- Create an **IAM role** with:
  - Trusted entity: **EC2**.
  - Permission policy: either
    - `AmazonS3FullAccess` (for experiments), or
    - A custom policy that allows `s3:ListBucket`, `s3:GetObject`, `s3:PutObject` *only* on your bucket, e.g. `arn:aws:s3:::data-new-ec2/*`.
- Attach this role to your EC2 instance:
  - EC2 → Instances → select instance → *Actions* → *Security* → *Modify IAM role* → choose your role.

With this, the instance can call S3 using instance metadata, without storing keys.

---

## 2. SSH into the EC2 instance

From your **local machine** (e.g. Windows PowerShell):

```bash
ssh -i "C:\path\to\your-key.pem" ubuntu@EC2_PUBLIC_IP
```

- Replace `C:\path\to\your-key.pem` with the path to your `.pem` file.
- Replace `EC2_PUBLIC_IP` with your instance’s public IP or DNS.

If it works, your shell prompt will look like:

```bash
ubuntu@ip-XX-XX-XX-XX:~$
```

---

## 3. Install system dependencies on EC2

Update packages and install tools:

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip unzip
```

---

## 4. Clone the UWSS repository and create virtualenv

In your EC2 shell:

```bash
cd ~
git clone https://github.com/duynguyenxc/Universal-Web-Scraping-System-high-level-update.git
cd Universal-Web-Scraping-System-high-level-update

python3 -m venv uwss-env
source uwss-env/bin/activate        # prompt will show (uwss-env)

pip install --upgrade pip
pip install -r requirements.txt
```

If you later want to **exit** the virtualenv:

```bash
deactivate
```

---

## 5. Configure UWSS on EC2

### 5.1. Edit domain configuration

Open and edit `config/config.yaml`:

```bash
nano config/config.yaml
```

Adjust:

- `domain_keywords`
- `negative_keywords`
- `contact_email`
- `user_agent`

Save and exit (`Ctrl+O`, Enter, `Ctrl+X` in nano).

### 5.2. Initialize the local SQLite database

From the project root (with virtualenv activated):

```bash
python -m src.uwss.cli db-init --db data/uwss.sqlite
```

---

## 6. Run the UWSS pipeline on EC2

These are typical commands (see `README.md` for more variants).

### 6.1. Discover documents from academic APIs

```bash
# Crossref
python -m src.uwss.cli crossref-lib-discover \
  --config config/config.yaml \
  --db data/uwss.sqlite \
  --max 100

# OpenAlex
python -m src.uwss.cli openalex-lib-discover \
  --config config/config.yaml \
  --db data/uwss.sqlite \
  --max 100

# Semantic Scholar
python -m src.uwss.cli semantic-scholar-lib-discover \
  --config config/config.yaml \
  --db data/uwss.sqlite \
  --max 100

# PubMed
python -m src.uwss.cli paperscraper-discover \
  --config config/config.yaml \
  --db data/uwss.sqlite \
  --source pubmed \
  --max 100

# arXiv
python -m src.uwss.cli paperscraper-discover \
  --config config/config.yaml \
  --db data/uwss.sqlite \
  --source arxiv \
  --max 100
```

### 6.2. Score, export, and fetch PDFs

```bash
# Score relevance
python -m src.uwss.cli score-keywords \
  --config config/config.yaml \
  --db data/uwss.sqlite \
  --min 0.0

# Export relevant subset to JSONL
python -m src.uwss.cli export \
  --db data/uwss.sqlite \
  --out data/corrosion_papers.jsonl \
  --require-match \
  --min-score 0.5 \
  --require-abstract \
  --min-abstract-length 80

# Fetch PDFs
python -m src.uwss.cli fetch \
  --db data/uwss.sqlite \
  --outdir data/files \
  --limit 20 \
  --config config/config.yaml
```

After this, all output lives under the `data/` directory in the project:

- `data/uwss.sqlite`
- `data/corrosion_papers.jsonl`
- `data/files/` (PDFs)
- other helper files if enabled.

---

## 7. Install AWS CLI on EC2

On Ubuntu 24.04, the `awscli` package from `apt` may not be available. Use one of the following.

### 7.1. Option A – Install via snap (simple)

```bash
sudo snap install aws-cli
aws --version
```

If you see a version string (e.g. `aws-cli/1.x`), it is installed.

### 7.2. Option B – Official AWS CLI v2 installer

Use this if `snap` is not available or fails.

```bash
cd ~
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
aws --version
```

You should see something like `aws-cli/2.x.y Python/3.x`.

### 7.3. Verify IAM identity (optional but recommended)

If you attached an IAM role with S3 permissions:

```bash
aws sts get-caller-identity
```

If this returns account and role information, the CLI can authenticate correctly.

---

## 8. Sync UWSS data from EC2 to S3

Assume:

- Project path on EC2:  
  `/home/ubuntu/Universal-Web-Scraping-System-high-level-update`
- All outputs are under:  
  `/home/ubuntu/Universal-Web-Scraping-System-high-level-update/data`
- S3 bucket: `data-new-ec2`
- Desired prefix in the bucket: `uwss-data/`

Then run **on EC2**:

```bash
aws s3 sync \
  /home/ubuntu/Universal-Web-Scraping-System-high-level-update/data \
  s3://data-new-ec2/uwss-data/
```

This will:

- Create `uwss-data/` in the `data-new-ec2` bucket (if it does not exist).
- Upload all files and subfolders from `data/` (SQLite DB, JSONL, PDFs, etc.).
- Only upload changed files on subsequent runs.

You can adjust the prefix to keep runs separated, for example:

```bash
aws s3 sync \
  /home/ubuntu/Universal-Web-Scraping-System-high-level-update/data \
  s3://data-new-ec2/uwss-data/runs/2025-11-22/
```

---

## 9. (Optional) Download data from S3 back to another machine

### 9.1. From S3 to a different EC2 instance

On the new EC2 instance (with AWS CLI and permissions configured):

```bash
aws s3 sync \
  s3://data-new-ec2/uwss-data/ \
  /home/ubuntu/uwss-data
```

### 9.2. From S3 to your local machine

On your local machine (with AWS CLI and credentials configured):

```bash
aws s3 sync \
  s3://data-new-ec2/uwss-data/ \
  C:\Users\YOUR_NAME\Downloads\uwss-data
```

Replace `YOUR_NAME` with your actual user name and adjust the path as needed.

---

## 10. Summary of the minimal EC2 → S3 workflow

1. **Launch EC2** with Ubuntu and attach an **IAM role** that can write to your S3 bucket.
2. **SSH in**, install Python tools, clone the **UWSS** repo, create and activate the virtualenv.
3. **Configure and run the UWSS pipeline** to populate `data/` (`db-init`, discover, score, export, fetch).
4. **Install AWS CLI** on EC2.
5. **Sync all results to S3** with a single command:

   ```bash
   aws s3 sync /home/ubuntu/Universal-Web-Scraping-System-high-level-update/data s3://data-new-ec2/uwss-data/
   ```

This is the pattern commonly used in real projects: **EC2 for compute**, **S3 as the durable data store**.


