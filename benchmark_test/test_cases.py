"""
test_cases.py
=============
All test data for the Locust load test.

  PROMPTS            – General-purpose LLM prompts (coding, reasoning, creative …)
  SQL_TEST_CASES     – Complex text-to-SQL scenarios with schema + sample data + question
  SYSTEM_PROMPT_SQL  – System message for the SQL generation task
  build_sql_prompt() – Formats a SQL test case into a user message
"""

PROMPTS = [

    # Short factual
    "What is FastAPI in two sentences?",
    "Explain REST API simply.",
    "What is vector search?",
    "Difference between CPU and GPU.",

    # Coding
    "Write a Python function to reverse a string.",
    "Write a Python function to remove duplicates from a list.",
    "Generate a binary search implementation in Python.",
    "Write a FastAPI endpoint for file upload.",
    "Create a pandas dataframe example with missing values.",

    # Reasoning
    "A train moves 60 km/h for 2 hours. How far did it travel?",
    "If 5 workers finish a job in 10 days, estimate time for 10 workers.",
    "Compare supervised and unsupervised learning.",

    # Long generation
    "Write a 300-word blog on AI in healthcare.",
    "Explain transformers architecture in detail.",
    "Describe Retrieval Augmented Generation with examples.",

    # Summarization
    "Summarize the benefits and risks of generative AI.",
    "Summarize Kubernetes in under 100 words.",

    # Structured output
    "Return a JSON object describing a laptop with keys: brand, cpu, ram, storage.",
    "Generate a JSON schema for an employee database.",

    # SQL / DB
    "Write an SQL query to find top 5 highest-paid employees.",
    "Explain database indexing with an example.",

    # DevOps / Infra
    "Explain Docker vs Kubernetes.",
    "What is load balancing?",
    "Describe CI/CD pipelines.",

    # Multilingual
    "Explain machine learning in Hindi.",
    "Explain neural networks in simple Bengali.",
    "Translate 'Artificial Intelligence is transforming healthcare' to Tamil.",

    # Creative
    "Write a short sci-fi story about an AI assistant.",
    "Generate a motivational quote about engineering.",

    # Analytical
    "Compare Llama, Gemma, and Qwen models.",
    "Explain quantization in LLM inference.",
]

# ──────────────────────────────────────────────────────────────
# TEXT-TO-SQL TEST CASES  (5 complex, real-world scenarios)
# Each entry: { "schema", "sample_data", "question" }
# ──────────────────────────────────────────────────────────────

SQL_TEST_CASES = [

    # ── TC-1: E-Commerce — Revenue & Retention ──────────────
    {
        "schema": """
-- E-Commerce Platform (PostgreSQL)

CREATE TABLE customers (
    customer_id    SERIAL PRIMARY KEY,
    email          VARCHAR(255) UNIQUE NOT NULL,
    full_name      VARCHAR(150) NOT NULL,
    signup_date    DATE NOT NULL,
    country_code   CHAR(2) NOT NULL,
    tier           VARCHAR(20) DEFAULT 'standard'  -- standard | premium | enterprise
);

CREATE TABLE products (
    product_id     SERIAL PRIMARY KEY,
    sku            VARCHAR(50) UNIQUE NOT NULL,
    name           VARCHAR(255) NOT NULL,
    category       VARCHAR(100) NOT NULL,
    subcategory    VARCHAR(100),
    unit_price     NUMERIC(10,2) NOT NULL,
    cost_price     NUMERIC(10,2) NOT NULL,
    stock_qty      INT NOT NULL DEFAULT 0,
    is_active      BOOLEAN DEFAULT TRUE,
    created_at     TIMESTAMP DEFAULT NOW()
);

CREATE TABLE orders (
    order_id       SERIAL PRIMARY KEY,
    customer_id    INT NOT NULL REFERENCES customers(customer_id),
    order_date     TIMESTAMP NOT NULL,
    status         VARCHAR(30) NOT NULL,  -- pending | confirmed | shipped | delivered | returned | cancelled
    shipping_fee   NUMERIC(8,2) DEFAULT 0,
    discount_pct   NUMERIC(5,2) DEFAULT 0,
    coupon_code    VARCHAR(50),
    payment_method VARCHAR(30)  -- credit_card | upi | net_banking | cod | wallet
);

CREATE TABLE order_items (
    item_id        SERIAL PRIMARY KEY,
    order_id       INT NOT NULL REFERENCES orders(order_id),
    product_id     INT NOT NULL REFERENCES products(product_id),
    quantity       INT NOT NULL,
    unit_price     NUMERIC(10,2) NOT NULL,
    returned_qty   INT DEFAULT 0
);

CREATE TABLE product_reviews (
    review_id      SERIAL PRIMARY KEY,
    product_id     INT NOT NULL REFERENCES products(product_id),
    customer_id    INT NOT NULL REFERENCES customers(customer_id),
    rating         SMALLINT CHECK (rating BETWEEN 1 AND 5),
    review_text    TEXT,
    created_at     TIMESTAMP DEFAULT NOW()
);
""",
        "sample_data": """
-- customers
INSERT INTO customers VALUES
(1, 'ananya.r@mail.com',   'Ananya Rao',      '2023-01-15', 'IN', 'premium'),
(2, 'john.d@mail.com',     'John Doe',         '2023-03-22', 'US', 'standard'),
(3, 'mei.chen@mail.com',   'Mei Chen',         '2022-11-05', 'SG', 'enterprise'),
(4, 'priya.s@mail.com',    'Priya Sharma',     '2023-06-10', 'IN', 'standard'),
(5, 'alex.m@mail.com',     'Alex Mueller',     '2024-01-02', 'DE', 'premium'),
(6, 'fatima.k@mail.com',   'Fatima Khan',      '2023-02-18', 'AE', 'standard'),
(7, 'raj.patel@mail.com',  'Raj Patel',        '2022-08-30', 'IN', 'premium'),
(8, 'lisa.wong@mail.com',  'Lisa Wong',        '2023-09-14', 'US', 'standard');

-- products
INSERT INTO products (product_id, sku, name, category, subcategory, unit_price, cost_price, stock_qty) VALUES
(101, 'ELEC-LAPTOP-001', 'ProBook 15 Laptop',       'Electronics', 'Laptops',       74999.00, 58000.00, 45),
(102, 'ELEC-PHONE-002',  'SmartX Pro Phone',         'Electronics', 'Smartphones',   34999.00, 22000.00, 120),
(103, 'FASH-SHOE-003',   'RunFlex Sports Shoes',     'Fashion',     'Footwear',       3499.00,  1800.00, 300),
(104, 'HOME-CHAIR-004',  'ErgoSit Office Chair',     'Home & Office','Furniture',     12999.00,  8500.00, 60),
(105, 'ELEC-EAR-005',    'BassBoost Earbuds',        'Electronics', 'Audio',          2499.00,  1100.00, 500),
(106, 'GROC-TEA-006',    'Himalayan Green Tea 250g', 'Grocery',     'Beverages',       349.00,   180.00, 1000),
(107, 'ELEC-TAB-007',    'SlimPad Tablet 10"',       'Electronics', 'Tablets',       22999.00, 15000.00, 80),
(108, 'FASH-BAG-008',    'UrbanPack Backpack',       'Fashion',     'Bags',           1999.00,  1050.00, 200);

-- orders (spanning Jan 2024 – May 2025)
INSERT INTO orders VALUES
(1001, 1, '2024-01-20 10:30:00', 'delivered',  99.00, 5.00,  'NEWYEAR5',  'credit_card'),
(1002, 2, '2024-02-14 14:15:00', 'delivered',   0.00, 0.00,  NULL,        'upi'),
(1003, 1, '2024-03-08 09:45:00', 'delivered',  49.00, 10.00, 'MARCH10',   'net_banking'),
(1004, 3, '2024-04-01 16:00:00', 'delivered',   0.00, 0.00,  NULL,        'credit_card'),
(1005, 4, '2024-05-12 11:20:00', 'returned',   99.00, 0.00,  NULL,        'cod'),
(1006, 5, '2024-06-25 13:30:00', 'delivered',   0.00, 15.00, 'SUMMER15',  'wallet'),
(1007, 1, '2024-07-04 18:00:00', 'delivered',  49.00, 0.00,  NULL,        'upi'),
(1008, 6, '2024-08-19 10:10:00', 'cancelled',   0.00, 0.00,  NULL,        'credit_card'),
(1009, 7, '2024-09-30 15:45:00', 'delivered',   0.00, 5.00,  'FESTIVE5',  'upi'),
(1010, 2, '2024-11-15 12:00:00', 'delivered',  99.00, 0.00,  NULL,        'credit_card'),
(1011, 3, '2025-01-10 08:30:00', 'shipped',     0.00, 10.00, 'JAN10',     'net_banking'),
(1012, 8, '2025-02-28 17:20:00', 'delivered',  49.00, 0.00,  NULL,        'wallet'),
(1013, 1, '2025-03-15 09:00:00', 'confirmed',   0.00, 0.00,  NULL,        'upi'),
(1014, 4, '2025-04-22 14:30:00', 'pending',    99.00, 5.00,  'APR5',      'cod'),
(1015, 7, '2025-05-01 10:00:00', 'confirmed',   0.00, 0.00,  NULL,        'credit_card');

-- order_items
INSERT INTO order_items (item_id, order_id, product_id, quantity, unit_price, returned_qty) VALUES
(1, 1001, 101, 1, 74999.00, 0),
(2, 1001, 105, 2,  2499.00, 0),
(3, 1002, 103, 1,  3499.00, 0),
(4, 1002, 106, 3,   349.00, 0),
(5, 1003, 102, 1, 34999.00, 0),
(6, 1003, 108, 1,  1999.00, 0),
(7, 1004, 101, 2, 74999.00, 0),
(8, 1004, 104, 1, 12999.00, 0),
(9, 1005, 107, 1, 22999.00, 1),
(10, 1006, 102, 1, 34999.00, 0),
(11, 1006, 105, 3,  2499.00, 0),
(12, 1007, 106, 5,   349.00, 0),
(13, 1007, 103, 2,  3499.00, 0),
(14, 1008, 104, 1, 12999.00, 0),
(15, 1009, 101, 1, 74999.00, 0),
(16, 1009, 108, 2,  1999.00, 0),
(17, 1010, 102, 1, 34999.00, 0),
(18, 1010, 107, 1, 22999.00, 0),
(19, 1011, 105, 4,  2499.00, 0),
(20, 1011, 106, 10,  349.00, 0),
(21, 1012, 103, 1,  3499.00, 0),
(22, 1013, 101, 1, 74999.00, 0),
(23, 1014, 104, 2, 12999.00, 0),
(24, 1015, 107, 1, 22999.00, 0),
(25, 1015, 105, 2,  2499.00, 0);

-- product_reviews
INSERT INTO product_reviews (review_id, product_id, customer_id, rating, review_text, created_at) VALUES
(1, 101, 1, 5, 'Excellent build and performance, worth every rupee.',          '2024-02-01 12:00:00'),
(2, 101, 7, 4, 'Good laptop but battery life could be better.',               '2024-10-15 09:00:00'),
(3, 102, 2, 3, 'Camera is average, but the processor is blazing fast.',        '2024-03-10 15:00:00'),
(4, 102, 5, 5, 'Best phone I have ever used. Period.',                         '2024-07-20 11:00:00'),
(5, 103, 2, 4, 'Comfortable for daily running, good arch support.',            '2024-03-01 10:00:00'),
(6, 105, 1, 5, 'Incredible bass for the price.',                               '2024-02-05 14:00:00'),
(7, 105, 3, 4, 'Good sound quality but ear tips could be softer.',             '2025-01-20 16:00:00'),
(8, 104, 4, 1, 'Armrest broke within a week. Very disappointed.',              '2024-06-01 08:00:00'),
(9, 107, 4, 2, 'Screen flickered and had to return. Poor QC.',                 '2024-05-20 17:00:00'),
(10, 106, 1, 5, 'Refreshing taste and great aroma.',                           '2024-08-10 13:00:00');
""",
        "question": (
            "For each calendar quarter in 2024, calculate: (a) total net revenue "
            "(after discount_pct and excluding orders with status 'cancelled' or 'returned'), "
            "(b) gross profit (net revenue minus cost of goods sold), "
            "(c) the repeat-purchase rate (percentage of customers who placed more than one "
            "delivered order up to and including that quarter), and "
            "(d) the top-selling product category by revenue in that quarter. "
            "Return results sorted by quarter."
        ),
    },

    # ── TC-2: Healthcare — Patient Analytics ────────────────
    {
        "schema": """
-- Hospital Management System (PostgreSQL)

CREATE TABLE departments (
    dept_id        SERIAL PRIMARY KEY,
    dept_name      VARCHAR(100) NOT NULL,
    floor_no       INT,
    head_doctor_id INT  -- FK added after doctors table
);

CREATE TABLE doctors (
    doctor_id      SERIAL PRIMARY KEY,
    full_name      VARCHAR(150) NOT NULL,
    specialization VARCHAR(100) NOT NULL,
    dept_id        INT REFERENCES departments(dept_id),
    license_no     VARCHAR(50) UNIQUE NOT NULL,
    hire_date      DATE NOT NULL,
    is_active      BOOLEAN DEFAULT TRUE
);

ALTER TABLE departments ADD CONSTRAINT fk_head_doc
    FOREIGN KEY (head_doctor_id) REFERENCES doctors(doctor_id);

CREATE TABLE patients (
    patient_id     SERIAL PRIMARY KEY,
    full_name      VARCHAR(150) NOT NULL,
    date_of_birth  DATE NOT NULL,
    gender         CHAR(1) CHECK (gender IN ('M','F','O')),
    blood_group    VARCHAR(5),
    phone          VARCHAR(20),
    city           VARCHAR(100),
    insurance_id   VARCHAR(50)
);

CREATE TABLE appointments (
    appt_id        SERIAL PRIMARY KEY,
    patient_id     INT NOT NULL REFERENCES patients(patient_id),
    doctor_id      INT NOT NULL REFERENCES doctors(doctor_id),
    appt_date      TIMESTAMP NOT NULL,
    appt_type      VARCHAR(30) NOT NULL,  -- walk_in | scheduled | emergency | follow_up
    status         VARCHAR(20) NOT NULL,   -- completed | no_show | cancelled | in_progress
    diagnosis_code VARCHAR(10),            -- ICD-10 code
    notes          TEXT
);

CREATE TABLE prescriptions (
    rx_id          SERIAL PRIMARY KEY,
    appt_id        INT NOT NULL REFERENCES appointments(appt_id),
    medicine_name  VARCHAR(200) NOT NULL,
    dosage         VARCHAR(100),
    duration_days  INT,
    quantity       INT
);

CREATE TABLE billing (
    bill_id        SERIAL PRIMARY KEY,
    patient_id     INT NOT NULL REFERENCES patients(patient_id),
    appt_id        INT REFERENCES appointments(appt_id),
    bill_date      DATE NOT NULL,
    total_amount   NUMERIC(12,2) NOT NULL,
    insurance_cover NUMERIC(12,2) DEFAULT 0,
    payment_status VARCHAR(20) NOT NULL  -- paid | pending | partially_paid | waived
);

CREATE TABLE lab_tests (
    test_id        SERIAL PRIMARY KEY,
    appt_id        INT NOT NULL REFERENCES appointments(appt_id),
    test_name      VARCHAR(150) NOT NULL,
    test_date      TIMESTAMP NOT NULL,
    result_value   VARCHAR(100),
    normal_range   VARCHAR(100),
    is_abnormal    BOOLEAN DEFAULT FALSE
);
""",
        "sample_data": """
-- departments
INSERT INTO departments (dept_id, dept_name, floor_no, head_doctor_id) VALUES
(1, 'Cardiology',       3, NULL),
(2, 'Orthopedics',      2, NULL),
(3, 'General Medicine',  1, NULL),
(4, 'Neurology',        4, NULL),
(5, 'Pediatrics',       1, NULL);

-- doctors
INSERT INTO doctors VALUES
(10, 'Dr. Kavitha Nair',     'Interventional Cardiology',  1, 'KA-MED-10234', '2015-06-01', TRUE),
(11, 'Dr. Arjun Mehta',      'Orthopedic Surgery',         2, 'MH-MED-22045', '2017-09-15', TRUE),
(12, 'Dr. Sneha Iyer',       'Internal Medicine',          3, 'KA-MED-30987', '2019-03-20', TRUE),
(13, 'Dr. Rajesh Kumar',     'Neurosurgery',               4, 'DL-MED-41122', '2012-01-10', TRUE),
(14, 'Dr. Pooja Deshmukh',   'Pediatric Cardiology',       5, 'MH-MED-55034', '2020-07-01', TRUE),
(15, 'Dr. Mohammed Farooq',  'Sports Medicine',            2, 'TN-MED-60211', '2018-11-25', TRUE);

UPDATE departments SET head_doctor_id = 10 WHERE dept_id = 1;
UPDATE departments SET head_doctor_id = 11 WHERE dept_id = 2;
UPDATE departments SET head_doctor_id = 12 WHERE dept_id = 3;
UPDATE departments SET head_doctor_id = 13 WHERE dept_id = 4;
UPDATE departments SET head_doctor_id = 14 WHERE dept_id = 5;

-- patients
INSERT INTO patients VALUES
(100, 'Ramesh Gupta',      '1965-04-12', 'M', 'B+',  '9876543210', 'Bangalore', 'INS-4001'),
(101, 'Sunita Devi',       '1978-11-30', 'F', 'O+',  '9876543211', 'Mysore',    'INS-4002'),
(102, 'Amit Joshi',        '1990-07-22', 'M', 'A-',  '9876543212', 'Bangalore', NULL),
(103, 'Lakshmi Pillai',    '1955-01-05', 'F', 'AB+', '9876543213', 'Chennai',   'INS-4003'),
(104, 'Vikram Singh',      '2000-09-18', 'M', 'O-',  '9876543214', 'Delhi',     'INS-4004'),
(105, 'Baby Anika Singh',  '2022-03-10', 'F', 'B+',  '9876543215', 'Delhi',     'INS-4004'),
(106, 'Deepa Menon',       '1985-06-28', 'F', 'A+',  '9876543216', 'Kochi',     NULL),
(107, 'Suresh Reddy',      '1970-12-15', 'M', 'B-',  '9876543217', 'Hyderabad', 'INS-4005');

-- appointments (2024-01 to 2025-05)
INSERT INTO appointments VALUES
(501, 100, 10, '2024-01-10 09:00:00', 'scheduled',  'completed', 'I25.1',  'Chronic ischemic heart disease, stable angina'),
(502, 101, 12, '2024-01-22 10:30:00', 'walk_in',    'completed', 'J06.9',  'Acute upper respiratory infection'),
(503, 100, 10, '2024-02-14 09:00:00', 'follow_up',  'completed', 'I25.1',  'Follow-up, stress test normal'),
(504, 102, 11, '2024-03-05 14:00:00', 'emergency',  'completed', 'S82.0',  'Fracture of patella, right knee'),
(505, 103, 13, '2024-03-18 11:00:00', 'scheduled',  'completed', 'G43.9',  'Migraine, unspecified'),
(506, 104, 15, '2024-04-02 16:00:00', 'scheduled',  'completed', 'M79.3',  'Panniculitis — sports injury evaluation'),
(507, 105, 14, '2024-04-20 10:00:00', 'scheduled',  'completed', 'Q21.1',  'Atrial septal defect follow-up'),
(508, 100, 10, '2024-05-15 09:00:00', 'follow_up',  'completed', 'I25.1',  'Angiogram scheduled'),
(509, 106, 12, '2024-06-10 13:00:00', 'walk_in',    'completed', 'E11.9',  'Type 2 diabetes initial diagnosis'),
(510, 102, 11, '2024-07-01 14:30:00', 'follow_up',  'completed', 'S82.0',  'Cast removal, physio started'),
(511, 107, 10, '2024-08-12 10:00:00', 'scheduled',  'completed', 'I10',    'Essential hypertension'),
(512, 103, 13, '2024-09-05 11:00:00', 'follow_up',  'no_show',   NULL,     'Patient did not arrive'),
(513, 101, 12, '2024-10-14 09:30:00', 'scheduled',  'completed', 'E78.5',  'Hyperlipidemia'),
(514, 106, 12, '2024-12-01 13:00:00', 'follow_up',  'completed', 'E11.9',  'HbA1c improved to 6.8'),
(515, 100, 10, '2025-01-20 09:00:00', 'follow_up',  'completed', 'I25.1',  'Post-angioplasty check, stable'),
(516, 105, 14, '2025-03-10 10:30:00', 'follow_up',  'completed', 'Q21.1',  'Echocardiogram normal'),
(517, 104, 15, '2025-04-22 15:00:00', 'scheduled',  'cancelled', NULL,     'Patient requested reschedule'),
(518, 107, 10, '2025-05-05 10:00:00', 'scheduled',  'in_progress','I10',   'BP monitoring visit');

-- prescriptions
INSERT INTO prescriptions VALUES
(1, 501, 'Aspirin 75mg',          'Once daily after food',    90,  90),
(2, 501, 'Atorvastatin 20mg',     'Once daily at bedtime',    90,  90),
(3, 502, 'Amoxicillin 500mg',     'Thrice daily',              7,  21),
(4, 504, 'Diclofenac 50mg',       'Twice daily after food',   14,  28),
(5, 504, 'Calcium + Vitamin D3',  'Once daily',               60,  60),
(6, 505, 'Sumatriptan 50mg',      'As needed, max 2/day',     30,  10),
(7, 508, 'Clopidogrel 75mg',      'Once daily',               30,  30),
(8, 509, 'Metformin 500mg',       'Twice daily with meals',   90, 180),
(9, 511, 'Amlodipine 5mg',        'Once daily morning',       30,  30),
(10, 513, 'Rosuvastatin 10mg',    'Once daily at bedtime',    60,  60),
(11, 514, 'Metformin 500mg',      'Twice daily with meals',   90, 180),
(12, 515, 'Aspirin 75mg',         'Once daily after food',    90,  90);

-- billing
INSERT INTO billing VALUES
(1, 100, 501, '2024-01-10', 3500.00,  2500.00, 'paid'),
(2, 101, 502, '2024-01-22', 1200.00,   800.00, 'paid'),
(3, 100, 503, '2024-02-14', 8500.00,  6000.00, 'paid'),
(4, 102, 504, '2024-03-05', 45000.00,     0.00, 'partially_paid'),
(5, 103, 505, '2024-03-18', 4200.00,  3000.00, 'paid'),
(6, 104, 506, '2024-04-02', 2800.00,  2000.00, 'paid'),
(7, 105, 507, '2024-04-20', 15000.00, 12000.00, 'paid'),
(8, 100, 508, '2024-05-15', 62000.00, 50000.00, 'paid'),
(9, 106, 509, '2024-06-10', 2200.00,      0.00, 'pending'),
(10, 102, 510, '2024-07-01', 3500.00,     0.00, 'paid'),
(11, 107, 511, '2024-08-12', 2000.00,  1500.00, 'paid'),
(12, 101, 513, '2024-10-14', 3800.00,  2800.00, 'paid'),
(13, 106, 514, '2024-12-01', 2500.00,      0.00, 'pending'),
(14, 100, 515, '2025-01-20', 5000.00,  4000.00, 'paid'),
(15, 105, 516, '2025-03-10', 8000.00,  6500.00, 'paid');

-- lab_tests
INSERT INTO lab_tests VALUES
(1, 501, 'Lipid Panel',            '2024-01-10 09:30:00', 'LDL: 165 mg/dL',   '< 100 mg/dL',    TRUE),
(2, 501, 'ECG',                    '2024-01-10 10:00:00', 'ST depression V4-V6','Normal sinus',   TRUE),
(3, 503, 'Treadmill Stress Test',  '2024-02-14 10:00:00', 'Negative',          'Negative',        FALSE),
(4, 504, 'X-Ray Right Knee',       '2024-03-05 14:30:00', 'Displaced fracture','No fracture',     TRUE),
(5, 505, 'MRI Brain',              '2024-03-18 12:00:00', 'No lesions',        'No lesions',      FALSE),
(6, 507, 'Echocardiogram',         '2024-04-20 10:30:00', 'ASD 8mm',           'No defect',       TRUE),
(7, 508, 'Coronary Angiogram',     '2024-05-15 10:00:00', 'LAD 70% stenosis',  'No stenosis',     TRUE),
(8, 509, 'HbA1c',                  '2024-06-10 13:30:00', '8.2%',              '< 5.7%',          TRUE),
(9, 509, 'Fasting Blood Sugar',    '2024-06-10 13:30:00', '186 mg/dL',         '70-100 mg/dL',    TRUE),
(10, 511, 'Serum Creatinine',      '2024-08-12 10:30:00', '1.1 mg/dL',         '0.7-1.3 mg/dL',   FALSE),
(11, 514, 'HbA1c',                 '2024-12-01 13:30:00', '6.8%',              '< 5.7%',          TRUE),
(12, 515, 'Lipid Panel',           '2025-01-20 09:30:00', 'LDL: 98 mg/dL',    '< 100 mg/dL',     FALSE),
(13, 516, 'Echocardiogram',        '2025-03-10 11:00:00', 'ASD closed',        'No defect',       FALSE);
""",
        "question": (
            "Write a SQL query to identify high-risk patients: those who have 3 or more "
            "completed appointments, at least 2 abnormal lab results, and total out-of-pocket "
            "expense (total_amount minus insurance_cover) exceeding 10000. For each such patient, "
            "return their name, age (computed from date_of_birth), number of distinct doctors seen, "
            "count of abnormal labs, total billed, total insurance covered, out-of-pocket amount, "
            "and their most recent diagnosis code with its appointment date. Order by out-of-pocket "
            "descending."
        ),
    },

    # ── TC-3: SaaS — Multi-Tenant Subscription Analytics ───
    {
        "schema": """
-- SaaS Platform — Multi-Tenant Subscription & Usage (PostgreSQL)

CREATE TABLE tenants (
    tenant_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name   VARCHAR(200) NOT NULL,
    industry       VARCHAR(100),
    country        VARCHAR(60),
    created_at     TIMESTAMP DEFAULT NOW(),
    is_active      BOOLEAN DEFAULT TRUE
);

CREATE TABLE plans (
    plan_id        SERIAL PRIMARY KEY,
    plan_name      VARCHAR(50) NOT NULL,        -- free | starter | professional | enterprise
    monthly_price  NUMERIC(10,2) NOT NULL,
    max_seats      INT,                          -- NULL = unlimited
    max_api_calls  INT,                          -- monthly limit; NULL = unlimited
    features       JSONB                         -- feature flags
);

CREATE TABLE subscriptions (
    sub_id         SERIAL PRIMARY KEY,
    tenant_id      UUID NOT NULL REFERENCES tenants(tenant_id),
    plan_id        INT NOT NULL REFERENCES plans(plan_id),
    start_date     DATE NOT NULL,
    end_date       DATE,                          -- NULL = active
    mrr            NUMERIC(10,2) NOT NULL,        -- monthly recurring revenue at subscription time
    seats_purchased INT NOT NULL DEFAULT 1,
    billing_cycle  VARCHAR(10) DEFAULT 'monthly', -- monthly | annual
    cancel_reason  TEXT
);

CREATE TABLE usage_events (
    event_id       BIGSERIAL PRIMARY KEY,
    tenant_id      UUID NOT NULL REFERENCES tenants(tenant_id),
    event_date     DATE NOT NULL,
    api_calls      INT NOT NULL DEFAULT 0,
    storage_mb     NUMERIC(10,2) DEFAULT 0,
    active_users   INT NOT NULL DEFAULT 0,
    compute_minutes NUMERIC(10,2) DEFAULT 0
);

CREATE TABLE invoices (
    invoice_id     SERIAL PRIMARY KEY,
    tenant_id      UUID NOT NULL REFERENCES tenants(tenant_id),
    sub_id         INT REFERENCES subscriptions(sub_id),
    invoice_date   DATE NOT NULL,
    amount         NUMERIC(10,2) NOT NULL,
    tax            NUMERIC(10,2) DEFAULT 0,
    status         VARCHAR(20) NOT NULL,          -- paid | overdue | void | refunded
    due_date       DATE NOT NULL
);

CREATE TABLE support_tickets (
    ticket_id      SERIAL PRIMARY KEY,
    tenant_id      UUID NOT NULL REFERENCES tenants(tenant_id),
    created_at     TIMESTAMP NOT NULL DEFAULT NOW(),
    resolved_at    TIMESTAMP,
    priority       VARCHAR(10) NOT NULL,          -- low | medium | high | critical
    category       VARCHAR(50),                   -- billing | bug | feature_request | onboarding | api
    satisfaction   SMALLINT CHECK (satisfaction BETWEEN 1 AND 5)
);
""",
        "sample_data": """
-- plans
INSERT INTO plans VALUES
(1, 'free',          0.00,    3,    1000,   '{"sso": false, "audit_log": false, "priority_support": false}'),
(2, 'starter',      49.00,   10,   50000,  '{"sso": false, "audit_log": false, "priority_support": false}'),
(3, 'professional', 199.00,  50,  500000,  '{"sso": true,  "audit_log": true,  "priority_support": false}'),
(4, 'enterprise',   799.00, NULL,    NULL,  '{"sso": true,  "audit_log": true,  "priority_support": true}');

-- tenants
INSERT INTO tenants (tenant_id, company_name, industry, country, created_at) VALUES
('a1b2c3d4-0001-4000-8000-000000000001', 'Acme Corp',        'Technology',     'US',     '2022-06-15'),
('a1b2c3d4-0002-4000-8000-000000000002', 'GlobalRetail Ltd', 'Retail',         'UK',     '2023-01-10'),
('a1b2c3d4-0003-4000-8000-000000000003', 'MediTech Inc',     'Healthcare',     'US',     '2023-03-22'),
('a1b2c3d4-0004-4000-8000-000000000004', 'FinanceHub AG',    'Finance',        'DE',     '2023-07-01'),
('a1b2c3d4-0005-4000-8000-000000000005', 'EduLearn Pvt',     'Education',      'IN',     '2023-09-05'),
('a1b2c3d4-0006-4000-8000-000000000006', 'QuickShip Co',     'Logistics',      'SG',     '2024-01-20'),
('a1b2c3d4-0007-4000-8000-000000000007', 'DataWorks LLC',    'Technology',     'US',     '2024-04-10'),
('a1b2c3d4-0008-4000-8000-000000000008', 'CloudNine SaaS',   'Technology',     'IN',     '2024-06-01');

-- subscriptions (history of upgrades, downgrades, churns)
INSERT INTO subscriptions (sub_id, tenant_id, plan_id, start_date, end_date, mrr, seats_purchased, billing_cycle, cancel_reason) VALUES
(1,  'a1b2c3d4-0001-4000-8000-000000000001', 2, '2022-06-15', '2023-02-28',  49.00,   5, 'monthly', 'Upgrading'),
(2,  'a1b2c3d4-0001-4000-8000-000000000001', 3, '2023-03-01', NULL,         199.00,  25, 'annual',  NULL),
(3,  'a1b2c3d4-0002-4000-8000-000000000002', 3, '2023-01-10', '2024-06-30', 199.00,  30, 'monthly', 'Too expensive'),
(4,  'a1b2c3d4-0002-4000-8000-000000000002', 2, '2024-07-01', NULL,          49.00,  10, 'monthly', NULL),
(5,  'a1b2c3d4-0003-4000-8000-000000000003', 4, '2023-03-22', NULL,         799.00,  80, 'annual',  NULL),
(6,  'a1b2c3d4-0004-4000-8000-000000000004', 3, '2023-07-01', NULL,         199.00,  40, 'annual',  NULL),
(7,  'a1b2c3d4-0005-4000-8000-000000000005', 1, '2023-09-05', '2024-03-31',   0.00,   3, 'monthly', 'Churned - no budget'),
(8,  'a1b2c3d4-0006-4000-8000-000000000006', 2, '2024-01-20', NULL,          49.00,   8, 'monthly', NULL),
(9,  'a1b2c3d4-0007-4000-8000-000000000007', 3, '2024-04-10', NULL,         199.00,  15, 'monthly', NULL),
(10, 'a1b2c3d4-0008-4000-8000-000000000008', 1, '2024-06-01', NULL,           0.00,   2, 'monthly', NULL);

-- usage_events (monthly aggregates for simplicity)
INSERT INTO usage_events (tenant_id, event_date, api_calls, storage_mb, active_users, compute_minutes) VALUES
('a1b2c3d4-0001-4000-8000-000000000001', '2024-10-01', 320000, 4500.00, 22, 1800.5),
('a1b2c3d4-0001-4000-8000-000000000001', '2024-11-01', 410000, 4800.00, 24, 2100.0),
('a1b2c3d4-0001-4000-8000-000000000001', '2024-12-01', 395000, 5100.00, 23, 1950.0),
('a1b2c3d4-0001-4000-8000-000000000001', '2025-01-01', 450000, 5400.00, 25, 2400.0),
('a1b2c3d4-0002-4000-8000-000000000002', '2024-10-01',  35000, 1200.00,  8,  300.0),
('a1b2c3d4-0002-4000-8000-000000000002', '2024-11-01',  28000, 1100.00,  6,  250.0),
('a1b2c3d4-0002-4000-8000-000000000002', '2024-12-01',  22000, 1050.00,  5,  200.0),
('a1b2c3d4-0002-4000-8000-000000000002', '2025-01-01',  18000,  980.00,  4,  150.0),
('a1b2c3d4-0003-4000-8000-000000000003', '2024-10-01', 980000, 12000.00, 72, 5600.0),
('a1b2c3d4-0003-4000-8000-000000000003', '2024-11-01',1050000, 13500.00, 75, 6200.0),
('a1b2c3d4-0003-4000-8000-000000000003', '2024-12-01',1120000, 14200.00, 78, 6800.0),
('a1b2c3d4-0003-4000-8000-000000000003', '2025-01-01',1200000, 15000.00, 80, 7400.0),
('a1b2c3d4-0004-4000-8000-000000000004', '2024-10-01', 280000, 3200.00, 35, 1500.0),
('a1b2c3d4-0004-4000-8000-000000000004', '2025-01-01', 310000, 3800.00, 38, 1700.0),
('a1b2c3d4-0006-4000-8000-000000000006', '2024-10-01',  42000,  800.00,  7,  400.0),
('a1b2c3d4-0006-4000-8000-000000000006', '2025-01-01',  48000,  950.00,  8,  450.0),
('a1b2c3d4-0007-4000-8000-000000000007', '2024-10-01', 380000, 2800.00, 14, 1600.0),
('a1b2c3d4-0007-4000-8000-000000000007', '2025-01-01', 520000, 3500.00, 15, 2200.0),
('a1b2c3d4-0008-4000-8000-000000000008', '2024-10-01',    800,   50.00,  2,   10.0),
('a1b2c3d4-0008-4000-8000-000000000008', '2025-01-01',    950,   55.00,  2,   12.0);

-- invoices
INSERT INTO invoices (tenant_id, sub_id, invoice_date, amount, tax, status, due_date) VALUES
('a1b2c3d4-0001-4000-8000-000000000001', 2, '2024-10-01', 199.00, 35.82, 'paid',    '2024-10-15'),
('a1b2c3d4-0001-4000-8000-000000000001', 2, '2024-11-01', 199.00, 35.82, 'paid',    '2024-11-15'),
('a1b2c3d4-0001-4000-8000-000000000001', 2, '2024-12-01', 199.00, 35.82, 'paid',    '2024-12-15'),
('a1b2c3d4-0001-4000-8000-000000000001', 2, '2025-01-01', 199.00, 35.82, 'paid',    '2025-01-15'),
('a1b2c3d4-0002-4000-8000-000000000002', 4, '2024-10-01',  49.00,  8.82, 'paid',    '2024-10-15'),
('a1b2c3d4-0002-4000-8000-000000000002', 4, '2024-11-01',  49.00,  8.82, 'overdue', '2024-11-15'),
('a1b2c3d4-0002-4000-8000-000000000002', 4, '2024-12-01',  49.00,  8.82, 'overdue', '2024-12-15'),
('a1b2c3d4-0003-4000-8000-000000000003', 5, '2024-10-01', 799.00,143.82, 'paid',    '2024-10-15'),
('a1b2c3d4-0003-4000-8000-000000000003', 5, '2025-01-01', 799.00,143.82, 'paid',    '2025-01-15'),
('a1b2c3d4-0004-4000-8000-000000000004', 6, '2024-10-01', 199.00, 35.82, 'paid',    '2024-10-15'),
('a1b2c3d4-0004-4000-8000-000000000004', 6, '2025-01-01', 199.00, 35.82, 'paid',    '2025-01-15'),
('a1b2c3d4-0006-4000-8000-000000000006', 8, '2025-01-01',  49.00,  8.82, 'paid',    '2025-01-15'),
('a1b2c3d4-0007-4000-8000-000000000007', 9, '2024-10-01', 199.00, 35.82, 'paid',    '2024-10-15'),
('a1b2c3d4-0007-4000-8000-000000000007', 9, '2025-01-01', 199.00, 35.82, 'overdue', '2025-01-15');

-- support_tickets
INSERT INTO support_tickets (tenant_id, created_at, resolved_at, priority, category, satisfaction) VALUES
('a1b2c3d4-0001-4000-8000-000000000001', '2024-10-05 09:00:00', '2024-10-05 11:30:00', 'medium', 'bug',             4),
('a1b2c3d4-0001-4000-8000-000000000001', '2024-11-12 14:00:00', '2024-11-13 10:00:00', 'high',   'api',             3),
('a1b2c3d4-0002-4000-8000-000000000002', '2024-10-20 08:00:00', '2024-10-22 16:00:00', 'high',   'billing',         2),
('a1b2c3d4-0002-4000-8000-000000000002', '2024-11-25 10:00:00', NULL,                  'critical','billing',         NULL),
('a1b2c3d4-0003-4000-8000-000000000003', '2024-10-15 07:00:00', '2024-10-15 08:00:00', 'low',    'feature_request',  5),
('a1b2c3d4-0003-4000-8000-000000000003', '2024-12-01 09:00:00', '2024-12-01 09:45:00', 'medium', 'api',             5),
('a1b2c3d4-0007-4000-8000-000000000007', '2025-01-05 11:00:00', NULL,                  'high',   'bug',             NULL),
('a1b2c3d4-0008-4000-8000-000000000008', '2024-12-10 13:00:00', '2024-12-12 09:00:00', 'medium', 'onboarding',      3);
""",
        "question": (
            "Build a churn-risk scoring query. For each currently active tenant (end_date IS NULL on "
            "their latest subscription), compute: (1) month-over-month percentage change in API calls "
            "between their two most recent usage records, (2) count of overdue invoices, "
            "(3) count of unresolved support tickets, (4) average satisfaction score across all their "
            "tickets, (5) a risk_score calculated as: (negative API growth rate * 2) + (overdue invoices * 15) "
            "+ (unresolved tickets * 20) - (avg satisfaction * 5), clamped between 0 and 100. "
            "Return tenant name, plan name, MRR, all 5 computed fields, and classify risk_level as "
            "'LOW' if score < 25, 'MEDIUM' if 25-50, 'HIGH' if 50-75, 'CRITICAL' if >= 75. "
            "Order by risk_score descending."
        ),
    },

    # ── TC-4: Supply Chain — Inventory & Logistics ──────────
    {
        "schema": """
-- Supply Chain & Logistics (PostgreSQL)

CREATE TABLE warehouses (
    warehouse_id   SERIAL PRIMARY KEY,
    name           VARCHAR(100) NOT NULL,
    city           VARCHAR(100) NOT NULL,
    state          VARCHAR(50),
    capacity_sqft  INT NOT NULL,
    manager_name   VARCHAR(150)
);

CREATE TABLE suppliers (
    supplier_id    SERIAL PRIMARY KEY,
    company_name   VARCHAR(200) NOT NULL,
    contact_email  VARCHAR(255),
    country        VARCHAR(60) NOT NULL,
    lead_time_days INT NOT NULL,          -- avg days from order to delivery
    reliability_score NUMERIC(3,2)        -- 0.00 to 1.00
);

CREATE TABLE materials (
    material_id    SERIAL PRIMARY KEY,
    name           VARCHAR(200) NOT NULL,
    category       VARCHAR(100),
    unit           VARCHAR(20) NOT NULL,  -- kg | litre | piece | meter
    min_stock      INT NOT NULL,          -- reorder point
    unit_cost      NUMERIC(10,2) NOT NULL
);

CREATE TABLE inventory (
    inv_id         SERIAL PRIMARY KEY,
    warehouse_id   INT NOT NULL REFERENCES warehouses(warehouse_id),
    material_id    INT NOT NULL REFERENCES materials(material_id),
    quantity       INT NOT NULL,
    last_restocked DATE,
    expiry_date    DATE                   -- NULL if non-perishable
);

CREATE TABLE purchase_orders (
    po_id          SERIAL PRIMARY KEY,
    supplier_id    INT NOT NULL REFERENCES suppliers(supplier_id),
    material_id    INT NOT NULL REFERENCES materials(material_id),
    warehouse_id   INT NOT NULL REFERENCES warehouses(warehouse_id),
    order_date     DATE NOT NULL,
    expected_date  DATE NOT NULL,
    delivered_date DATE,
    quantity       INT NOT NULL,
    total_cost     NUMERIC(12,2) NOT NULL,
    status         VARCHAR(20) NOT NULL   -- placed | in_transit | delivered | delayed | cancelled
);

CREATE TABLE shipments (
    shipment_id    SERIAL PRIMARY KEY,
    warehouse_id   INT NOT NULL REFERENCES warehouses(warehouse_id),
    destination    VARCHAR(200) NOT NULL,
    ship_date      DATE NOT NULL,
    delivery_date  DATE,
    carrier        VARCHAR(100),
    weight_kg      NUMERIC(10,2),
    freight_cost   NUMERIC(10,2),
    status         VARCHAR(20) NOT NULL   -- dispatched | in_transit | delivered | returned
);

CREATE TABLE shipment_items (
    id             SERIAL PRIMARY KEY,
    shipment_id    INT NOT NULL REFERENCES shipments(shipment_id),
    material_id    INT NOT NULL REFERENCES materials(material_id),
    quantity       INT NOT NULL
);
""",
        "sample_data": """
-- warehouses
INSERT INTO warehouses VALUES
(1, 'Bangalore Central Hub',  'Bangalore', 'Karnataka',  50000, 'Vikram Joshi'),
(2, 'Mumbai Port Warehouse',  'Mumbai',    'Maharashtra', 75000, 'Priya Desai'),
(3, 'Delhi NCR Distribution', 'Gurgaon',   'Haryana',     60000, 'Arun Kapoor'),
(4, 'Chennai Logistics Park', 'Chennai',   'Tamil Nadu',  40000, 'Lakshmi Narayan');

-- suppliers
INSERT INTO suppliers VALUES
(1, 'SteelWorks India Pvt Ltd',   'sales@steelworks.in',    'IN', 14, 0.92),
(2, 'ChemPure Reagents GmbH',    'orders@chempure.de',     'DE', 30, 0.88),
(3, 'PackRight Plastics',         'biz@packright.com',      'CN', 21, 0.75),
(4, 'GreenAgri Supplies',         'contact@greenagri.in',   'IN',  7, 0.95),
(5, 'TechComponents Korea',       'export@techcomp.kr',     'KR', 25, 0.82);

-- materials
INSERT INTO materials VALUES
(1, 'Cold Rolled Steel Sheet 2mm',  'Raw Metal',     'kg',    5000, 85.00),
(2, 'Industrial Solvent IPA',       'Chemicals',     'litre', 500,  220.00),
(3, 'HDPE Granules',                'Plastics',      'kg',    3000, 110.00),
(4, 'Organic Fertilizer NPK',      'Agriculture',   'kg',    2000, 45.00),
(5, 'PCB Board FR4 1.6mm',         'Electronics',   'piece', 1000, 350.00),
(6, 'Corrugated Box 12x10x8',      'Packaging',     'piece', 10000, 18.00),
(7, 'Lithium Battery Cell 3.7V',   'Electronics',   'piece', 2000, 520.00),
(8, 'Wheat Flour (Atta) 50kg bag', 'Food',          'piece', 200,  1250.00);

-- inventory
INSERT INTO inventory VALUES
(1,  1, 1, 12000, '2025-04-15', NULL),
(2,  1, 5,  800,  '2025-03-20', NULL),
(3,  1, 6, 15000, '2025-05-01', NULL),
(4,  2, 1,  8000, '2025-04-10', NULL),
(5,  2, 3,  2500, '2025-03-25', NULL),
(6,  2, 7,  1800, '2025-04-20', NULL),
(7,  3, 4,  1500, '2025-04-28', '2025-10-28'),
(8,  3, 6, 12000, '2025-05-05', NULL),
(9,  3, 2,   300, '2025-03-01', '2025-09-01'),
(10, 4, 5,  1200, '2025-05-10', NULL),
(11, 4, 8,   150, '2025-04-22', '2025-07-22'),
(12, 1, 7,   500, '2025-02-15', NULL),
(13, 2, 2,   450, '2025-04-05', '2025-10-05'),
(14, 3, 1,  3000, '2025-05-01', NULL);

-- purchase_orders
INSERT INTO purchase_orders VALUES
(1, 1, 1, 1, '2025-03-01', '2025-03-15', '2025-03-14', 10000, 850000.00,  'delivered'),
(2, 1, 1, 2, '2025-03-05', '2025-03-19', '2025-03-22',  8000, 680000.00,  'delayed'),
(3, 3, 3, 2, '2025-03-10', '2025-03-31', '2025-04-02',  5000, 550000.00,  'delayed'),
(4, 4, 4, 3, '2025-04-01', '2025-04-08', '2025-04-07',  3000, 135000.00,  'delivered'),
(5, 5, 5, 1, '2025-04-05', '2025-04-30', '2025-04-28',  2000, 700000.00,  'delivered'),
(6, 5, 7, 2, '2025-04-10', '2025-05-05', NULL,           3000, 1560000.00, 'in_transit'),
(7, 2, 2, 3, '2025-04-15', '2025-05-15', NULL,           1000, 220000.00,  'in_transit'),
(8, 1, 1, 3, '2025-04-20', '2025-05-04', '2025-05-01',  5000, 425000.00,  'delivered'),
(9, 3, 6, 1, '2025-04-25', '2025-05-16', NULL,          20000, 360000.00,  'placed'),
(10, 4, 8, 4, '2025-05-01', '2025-05-08', NULL,           500, 625000.00,  'placed'),
(11, 5, 5, 4, '2025-05-05', '2025-05-30', NULL,          1500, 525000.00,  'placed'),
(12, 1, 1, 1, '2025-05-10', '2025-05-24', NULL,           6000, 510000.00, 'in_transit');

-- shipments
INSERT INTO shipments VALUES
(1, 1, 'Hyderabad Factory',       '2025-04-01', '2025-04-03', 'BlueDart',      2500.00, 18500.00, 'delivered'),
(2, 2, 'Pune Assembly Plant',     '2025-04-05', '2025-04-06', 'DTDC',          1800.00, 12000.00, 'delivered'),
(3, 3, 'Lucknow Agri Center',    '2025-04-10', '2025-04-13', 'Delhivery',     3200.00, 22000.00, 'delivered'),
(4, 1, 'Coimbatore Warehouse',   '2025-04-18', '2025-04-20', 'FedEx',         1500.00, 25000.00, 'delivered'),
(5, 2, 'Ahmedabad Retail Hub',   '2025-05-01', NULL,          'BlueDart',      2200.00, 16000.00, 'in_transit'),
(6, 4, 'Vizag Port Export',      '2025-05-05', NULL,          'Maersk',        5000.00, 85000.00, 'in_transit'),
(7, 3, 'Jaipur Distribution',    '2025-05-08', NULL,          'Delhivery',     2800.00, 19000.00, 'dispatched'),
(8, 1, 'Hyderabad Factory',      '2025-05-10', NULL,          'BlueDart',      1200.00, 9500.00,  'dispatched');

-- shipment_items
INSERT INTO shipment_items VALUES
(1,  1, 1, 3000),
(2,  1, 5,  500),
(3,  2, 3, 2000),
(4,  2, 7,  800),
(5,  3, 4, 2500),
(6,  3, 6, 5000),
(7,  4, 6, 3000),
(8,  4, 5,  200),
(9,  5, 1, 2000),
(10, 5, 3, 1500),
(11, 6, 5,  800),
(12, 6, 8,  100),
(13, 7, 6, 4000),
(14, 7, 4, 1000),
(15, 8, 1, 1500),
(16, 8, 7,  300);
""",
        "question": (
            "Generate a supply chain risk report. For each material, calculate: "
            "(a) total current stock across all warehouses, "
            "(b) whether it is below the min_stock reorder point (flag as 'CRITICAL' if stock < 50% of min_stock, "
            "'LOW' if between 50%-100%, 'OK' if above), "
            "(c) incoming quantity from purchase orders that are 'placed' or 'in_transit', "
            "(d) days until earliest expiry (NULL if non-perishable), "
            "(e) the average supplier lead time weighted by the number of POs from each supplier for that material, "
            "(f) on-time delivery rate for that material (percentage of delivered POs where delivered_date <= expected_date), "
            "and (g) total outbound quantity currently dispatched or in transit from shipments. "
            "Order by stock_status priority (CRITICAL first, then LOW, then OK), "
            "then by total stock ascending."
        ),
    },

    # ── TC-5: Fintech — Transaction Fraud & Compliance ──────
    {
        "schema": """
-- Fintech Payment Platform (PostgreSQL)

CREATE TABLE merchants (
    merchant_id    SERIAL PRIMARY KEY,
    business_name  VARCHAR(200) NOT NULL,
    mcc_code       VARCHAR(10) NOT NULL,       -- Merchant Category Code
    category       VARCHAR(100) NOT NULL,
    city           VARCHAR(100),
    country        CHAR(2) NOT NULL,
    onboarded_at   DATE NOT NULL,
    kyc_status     VARCHAR(20) NOT NULL,        -- verified | pending | rejected | suspended
    risk_tier      VARCHAR(10) DEFAULT 'medium' -- low | medium | high
);

CREATE TABLE accounts (
    account_id     SERIAL PRIMARY KEY,
    holder_name    VARCHAR(150) NOT NULL,
    account_type   VARCHAR(20) NOT NULL,        -- savings | current | wallet | credit
    currency       CHAR(3) NOT NULL DEFAULT 'INR',
    balance        NUMERIC(14,2) NOT NULL,
    kyc_verified   BOOLEAN DEFAULT FALSE,
    created_at     TIMESTAMP NOT NULL
);

CREATE TABLE transactions (
    txn_id         BIGSERIAL PRIMARY KEY,
    from_account   INT REFERENCES accounts(account_id),
    to_account     INT REFERENCES accounts(account_id),
    merchant_id    INT REFERENCES merchants(merchant_id),
    txn_type       VARCHAR(20) NOT NULL,        -- purchase | transfer | withdrawal | refund | topup
    amount         NUMERIC(14,2) NOT NULL,
    currency       CHAR(3) NOT NULL DEFAULT 'INR',
    txn_timestamp  TIMESTAMP NOT NULL,
    channel        VARCHAR(20) NOT NULL,        -- app | web | pos | atm | api
    status         VARCHAR(20) NOT NULL,        -- success | failed | reversed | pending
    ip_address     VARCHAR(45),
    device_id      VARCHAR(100),
    location_lat   NUMERIC(9,6),
    location_lon   NUMERIC(9,6)
);

CREATE TABLE fraud_flags (
    flag_id        SERIAL PRIMARY KEY,
    txn_id         BIGINT NOT NULL REFERENCES transactions(txn_id),
    rule_code      VARCHAR(30) NOT NULL,        -- velocity_breach | geo_anomaly | amount_spike | device_mismatch | blocklist_hit
    severity       VARCHAR(10) NOT NULL,        -- low | medium | high | critical
    flagged_at     TIMESTAMP NOT NULL DEFAULT NOW(),
    reviewed       BOOLEAN DEFAULT FALSE,
    analyst_notes  TEXT,
    resolution     VARCHAR(20)                  -- confirmed_fraud | false_positive | escalated | pending
);

CREATE TABLE chargebacks (
    cb_id          SERIAL PRIMARY KEY,
    txn_id         BIGINT NOT NULL REFERENCES transactions(txn_id),
    merchant_id    INT NOT NULL REFERENCES merchants(merchant_id),
    reason_code    VARCHAR(10) NOT NULL,        -- 4837 | 4853 | 4863 | 10.4 | 13.1
    amount         NUMERIC(14,2) NOT NULL,
    filed_date     DATE NOT NULL,
    resolved_date  DATE,
    outcome        VARCHAR(20)                  -- won_by_merchant | won_by_customer | pending
);

CREATE TABLE compliance_alerts (
    alert_id       SERIAL PRIMARY KEY,
    account_id     INT NOT NULL REFERENCES accounts(account_id),
    alert_type     VARCHAR(30) NOT NULL,        -- aml_threshold | pep_match | sanctions_hit | unusual_pattern | structuring
    alert_date     DATE NOT NULL,
    amount_involved NUMERIC(14,2),
    status         VARCHAR(20) NOT NULL,        -- open | investigating | closed_clean | sar_filed
    assigned_to    VARCHAR(100)
);
""",
        "sample_data": """
-- merchants
INSERT INTO merchants VALUES
(1, 'QuickMart Retail',        '5411', 'Grocery',           'Bangalore', 'IN', '2022-01-10', 'verified',  'low'),
(2, 'FuelStation 24x7',        '5542', 'Fuel',              'Mumbai',    'IN', '2022-03-15', 'verified',  'low'),
(3, 'LuxeWatch Gallery',       '5944', 'Jewelry & Watches', 'Delhi',     'IN', '2023-06-20', 'verified',  'high'),
(4, 'GameZone Digital',         '5816', 'Digital Goods',     'Online',    'IN', '2023-09-01', 'verified',  'medium'),
(5, 'ShadyExports Ltd',        '5999', 'Miscellaneous',     'Kolkata',   'IN', '2024-01-05', 'suspended', 'high'),
(6, 'CloudHostPro',             '7372', 'SaaS / IT',        'Hyderabad', 'IN', '2023-02-28', 'verified',  'low'),
(7, 'PharmaPlus Online',       '5912', 'Pharmacy',          'Chennai',   'IN', '2022-08-14', 'verified',  'medium');

-- accounts
INSERT INTO accounts VALUES
(1001, 'Rahul Verma',       'savings',  'INR',  185000.00, TRUE,  '2021-06-15 10:00:00'),
(1002, 'Sneha Reddy',       'current',  'INR',  520000.00, TRUE,  '2022-01-20 09:00:00'),
(1003, 'Ali Mohammed',      'wallet',   'INR',   12500.00, TRUE,  '2023-03-10 14:00:00'),
(1004, 'Priyanka Gupta',    'savings',  'INR',   67000.00, TRUE,  '2022-07-05 11:00:00'),
(1005, 'Deepak Jain',       'credit',   'INR',  -45000.00, TRUE,  '2021-11-30 08:00:00'),
(1006, 'Kavya Nair',        'savings',  'INR',  340000.00, TRUE,  '2023-01-22 16:00:00'),
(1007, 'Suspicious User X', 'wallet',   'INR',   95000.00, FALSE, '2024-06-01 02:00:00'),
(1008, 'Merchant Escrow 1', 'current',  'INR', 2500000.00, TRUE,  '2022-01-10 09:00:00'),
(1009, 'Merchant Escrow 5', 'current',  'INR',  180000.00, TRUE,  '2024-01-05 09:00:00');

-- transactions
INSERT INTO transactions VALUES
(10001, 1001, 1008, 1, 'purchase',   2350.00,   'INR', '2025-04-01 10:15:00', 'app', 'success',  '103.21.5.10',  'dev-001', 12.9716, 77.5946),
(10002, 1001, 1008, 2, 'purchase',   4200.00,   'INR', '2025-04-01 14:30:00', 'pos', 'success',  NULL,           'pos-002', 19.0760, 72.8777),
(10003, 1002, NULL, NULL,'transfer', 50000.00,  'INR', '2025-04-02 09:00:00', 'web', 'success',  '49.36.12.88',  'dev-003', NULL,    NULL),
(10004, 1003, 1008, 4, 'purchase',    999.00,   'INR', '2025-04-02 22:10:00', 'app', 'success',  '182.70.4.22',  'dev-004', 12.9716, 77.5946),
(10005, 1004, 1008, 1, 'purchase',   1850.00,   'INR', '2025-04-03 11:00:00', 'app', 'success',  '103.21.5.55',  'dev-005', 12.9716, 77.5946),
(10006, 1007, 1009, 5, 'purchase',  85000.00,   'INR', '2025-04-03 02:30:00', 'web', 'success',  '185.220.3.1',  'dev-099', 22.5726, 88.3639),
(10007, 1007, 1009, 5, 'purchase',  92000.00,   'INR', '2025-04-03 02:35:00', 'web', 'success',  '185.220.3.1',  'dev-099', 22.5726, 88.3639),
(10008, 1007, 1009, 5, 'purchase',  78000.00,   'INR', '2025-04-03 02:42:00', 'web', 'success',  '185.220.3.1',  'dev-099', 22.5726, 88.3639),
(10009, 1005, 1008, 3, 'purchase', 175000.00,   'INR', '2025-04-04 16:00:00', 'pos', 'success',  NULL,           'pos-010', 28.6139, 77.2090),
(10010, 1005, 1008, 3, 'purchase', 220000.00,   'INR', '2025-04-04 16:05:00', 'pos', 'success',  NULL,           'pos-010', 28.6139, 77.2090),
(10011, 1002, 1008, 6, 'purchase',  15000.00,   'INR', '2025-04-05 10:00:00', 'web', 'success',  '49.36.12.88',  'dev-003', 17.3850, 78.4867),
(10012, 1006, NULL, NULL,'transfer',245000.00,  'INR', '2025-04-05 03:00:00', 'app', 'success',  '103.50.8.12',  'dev-006', 10.0159, 76.3419),
(10013, 1006, NULL, NULL,'transfer',  48000.00, 'INR', '2025-04-05 03:12:00', 'app', 'success',  '103.50.8.12',  'dev-006', 10.0159, 76.3419),
(10014, 1006, NULL, NULL,'transfer',  49500.00, 'INR', '2025-04-05 03:25:00', 'app', 'success',  '103.50.8.12',  'dev-006', 10.0159, 76.3419),
(10015, 1001, 1008, 7, 'purchase',   3800.00,   'INR', '2025-04-06 12:00:00', 'app', 'success',  '103.21.5.10',  'dev-001', 12.9716, 77.5946),
(10016, 1003, NULL, NULL,'topup',    10000.00,  'INR', '2025-04-06 18:00:00', 'app', 'success',  '182.70.4.22',  'dev-004', 12.9716, 77.5946),
(10017, 1004, 1008, 7, 'purchase',   5200.00,   'INR', '2025-04-07 09:30:00', 'web', 'success',  '103.21.5.55',  'dev-005', 12.9716, 77.5946),
(10018, 1002, 1008, 1, 'purchase',   3100.00,   'INR', '2025-04-07 11:15:00', 'pos', 'success',  NULL,           'pos-011', 19.0760, 72.8777),
(10019, 1007, 1009, 5, 'purchase',  65000.00,   'INR', '2025-04-08 01:50:00', 'api', 'failed',   '91.134.10.5',  'dev-100', 55.7558, 37.6173),
(10020, 1001, 1008, 2, 'purchase',   3900.00,   'INR', '2025-04-08 17:00:00', 'pos', 'success',  NULL,           'pos-002', 12.9716, 77.5946);

-- fraud_flags
INSERT INTO fraud_flags (txn_id, rule_code, severity, flagged_at, reviewed, analyst_notes, resolution) VALUES
(10006, 'velocity_breach',  'high',     '2025-04-03 02:31:00', TRUE,  '3 txns in 12 min from same device to suspended merchant',  'confirmed_fraud'),
(10007, 'velocity_breach',  'high',     '2025-04-03 02:36:00', TRUE,  'Continuation of velocity pattern',                          'confirmed_fraud'),
(10008, 'amount_spike',     'critical', '2025-04-03 02:43:00', TRUE,  '78K from wallet account, unusual for account profile',      'confirmed_fraud'),
(10009, 'amount_spike',     'high',     '2025-04-04 16:01:00', TRUE,  '175K luxury purchase on credit exceeding pattern',           'false_positive'),
(10010, 'velocity_breach',  'medium',   '2025-04-04 16:06:00', TRUE,  'Second large txn within 5 min, same POS',                   'false_positive'),
(10012, 'amount_spike',     'high',     '2025-04-05 03:01:00', FALSE, NULL,                                                        'pending'),
(10013, 'structuring',      'critical', '2025-04-05 03:13:00', FALSE, NULL,                                                        'pending'),
(10014, 'structuring',      'critical', '2025-04-05 03:26:00', FALSE, NULL,                                                        'pending'),
(10019, 'geo_anomaly',      'high',     '2025-04-08 01:51:00', TRUE,  'IP geolocation France, prev txns from India',                'confirmed_fraud');

-- chargebacks
INSERT INTO chargebacks VALUES
(1, 10006, 5, '4837', 85000.00,  '2025-04-10', '2025-04-25', 'won_by_customer'),
(2, 10007, 5, '4837', 92000.00,  '2025-04-10', '2025-04-25', 'won_by_customer'),
(3, 10008, 5, '4863', 78000.00,  '2025-04-10', NULL,         'pending'),
(4, 10009, 3, '10.4', 175000.00, '2025-04-15', '2025-05-01', 'won_by_merchant'),
(5, 10010, 3, '10.4', 220000.00, '2025-04-15', '2025-05-01', 'won_by_merchant');

-- compliance_alerts
INSERT INTO compliance_alerts VALUES
(1, 1007, 'aml_threshold',   '2025-04-03', 255000.00,  'sar_filed',     'Analyst Meera'),
(2, 1007, 'sanctions_hit',   '2025-04-03', NULL,        'investigating', 'Analyst Meera'),
(3, 1006, 'structuring',     '2025-04-05', 342500.00,   'open',          NULL),
(4, 1006, 'unusual_pattern', '2025-04-05', 342500.00,   'open',          NULL),
(5, 1005, 'aml_threshold',   '2025-04-04', 395000.00,   'closed_clean',  'Analyst Vikram');
""",
        "question": (
            "Create a comprehensive merchant risk assessment. For each merchant, calculate: "
            "(a) total transaction volume and value (only 'success' status), "
            "(b) number and total value of chargebacks, and the chargeback rate as percentage of "
            "successful transaction count, (c) count of fraud flags grouped by severity (high + critical), "
            "(d) count of associated accounts with open or investigating compliance alerts, "
            "(e) a composite risk score: (chargeback_rate * 30) + (high_critical_fraud_flags * 10) + "
            "(CASE WHEN kyc_status = 'suspended' THEN 40 ELSE 0 END) + "
            "(open_compliance_alerts * 15), capped at 100. "
            "Return merchant name, category, kyc_status, all computed metrics, the risk score, and "
            "classify as 'BLOCK' if score >= 80, 'REVIEW' if 40-79, 'MONITOR' if 10-39, 'CLEAR' if < 10. "
            "Exclude merchants with zero transactions. Order by risk score descending."
        ),
    },
]

# ──────────────────────────────────────────────────────────────
# Build the text-to-SQL prompt for a given test case
# ──────────────────────────────────────────────────────────────
SYSTEM_PROMPT_SQL = (
    "You are an expert SQL developer. Given the database schema and sample data below, "
    "write a single PostgreSQL query that answers the user's question. "
    "Return ONLY the SQL query — no explanations, no markdown fences."
)

def build_sql_prompt(tc):
    return (
        f"### DATABASE SCHEMA\n{tc['schema']}\n\n"
        f"### SAMPLE DATA\n{tc['sample_data']}\n\n"
        f"### QUESTION\n{tc['question']}\n\n"
        "Write the SQL query."
    )
