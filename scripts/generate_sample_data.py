import random
from datetime import date, timedelta
from faker import Faker
import psycopg2

fake = Faker("en_IN")

import os

db_host = os.environ.get("DB_HOST", "localhost")
db_port = os.environ.get("DB_PORT", "5432")
db_name = os.environ.get("DB_NAME", "ai_db_assistant")
db_user = os.environ.get("DB_USER", "postgres")
db_password = os.environ.get("DB_PASSWORD", "")

conn = psycopg2.connect(
    host=db_host,
    port=db_port,
    database=db_name,
    user=db_user,
    password=db_password
)

cursor = conn.cursor()

print("Connected to PostgreSQL")

cursor.execute("""
TRUNCATE TABLE
maintenance_requests,
payments,
expenses,
tenants,
rooms,
properties,
owners
RESTART IDENTITY CASCADE;
""")

owner_ids = []

owner_cities = [
    "Hyderabad",
    "Bangalore",
    "Chennai",
    "Pune"
]

for _ in range(10):

    cursor.execute("""
        INSERT INTO owners
        (
            owner_name,
            phone,
            email,
            city
        )
        VALUES (%s,%s,%s,%s)
        RETURNING owner_id
    """,
    (
        fake.name(),
        fake.phone_number()[:15],
        fake.email(),
        random.choice(owner_cities)
    ))

    owner_ids.append(
        cursor.fetchone()[0]
    )

conn.commit()

print("Owners inserted")


property_ids = []

pg_names = [
    "Sai PG",
    "Sri Lakshmi PG",
    "Techies PG",
    "Comfort Stay",
    "Metro PG",
    "Green Nest PG",
    "Elite Living PG",
    "Happy Homes PG",
    "Royal Residency",
    "Urban Nest"
]

property_types = [
    "Men",
    "Women",
    "Co-Living"
]

for _ in range(25):

    owner_id = random.choice(owner_ids)

    cursor.execute("""
        INSERT INTO properties
        (
            owner_id,
            property_name,
            address,
            city,
            total_rooms,
            total_beds,
            status,
            property_type
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        RETURNING property_id
    """,
    (
        owner_id,
        random.choice(pg_names),
        fake.address(),
        random.choice(owner_cities),
        random.randint(8,20),
        random.randint(30,80),
        "Active",
        random.choice(property_types)
    ))

    property_ids.append(
        cursor.fetchone()[0]
    )

conn.commit()

print("Properties inserted")

room_ids = []

rent_map = {
    1: 12000,
    2: 8500,
    3: 7000,
    4: 6000,
    5: 5000
}

room_counter = 1

for property_id in property_ids:

    room_count = random.randint(3,5)

    for _ in range(room_count):

        sharing = random.randint(1,5)

        occupied = random.randint(
            0,
            sharing
        )

        cursor.execute("""
            INSERT INTO rooms
            (
                property_id,
                room_no,
                sharing_type,
                capacity,
                occupied_beds,
                rent_per_bed,
                status
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            RETURNING room_id
        """,
        (
            property_id,
            f"R{room_counter}",
            sharing,
            sharing,
            occupied,
            rent_map[sharing],
            "Occupied" if occupied > 0 else "Vacant"
        ))

        room_ids.append(
            cursor.fetchone()[0]
        )

        room_counter += 1

conn.commit()

print("Rooms inserted")


tenant_ids = []

statuses = [
    "Active",
    "Active",
    "Active",
    "Notice Period",
    "Vacated"
]

occupations = [
    "Software Engineer",
    "Data Analyst",
    "Student",
    "Teacher",
    "Accountant",
    "Working Professional",
    "Job Seeker"
]

for _ in range(50):

    room_id = random.choice(room_ids)

    cursor.execute("""
        INSERT INTO tenants
        (
            tenant_name,
            phone,
            room_id,
            joining_date,
            leaving_date,
            status,
            emergency_contact,
            occupation
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        RETURNING tenant_id
    """,
    (
        fake.name(),
        fake.phone_number()[:15],
        room_id,
        fake.date_between(
            start_date="-2y",
            end_date="today"
        ),
        None,
        random.choice(statuses),
        fake.phone_number()[:15],
        random.choice(occupations)
    ))

    tenant_ids.append(
        cursor.fetchone()[0]
    )

conn.commit()

print("Tenants inserted")



payment_months = [
    ("Jul", 2025),
    ("Aug", 2025),
    ("Sep", 2025),
    ("Oct", 2025),
    ("Nov", 2025),
    ("Dec", 2025),
    ("Jan", 2026),
    ("Feb", 2026),
    ("Mar", 2026),
    ("Apr", 2026),
    ("May", 2026),
    ("Jun", 2026)
]

payment_statuses = [
    "Paid",
    "Paid",
    "Paid",
    "Pending",
    "Overdue",
    "Partially Paid"
]

for tenant_id in tenant_ids:

    cursor.execute("""
        SELECT r.rent_per_bed
        FROM tenants t
        JOIN rooms r
        ON t.room_id = r.room_id
        WHERE t.tenant_id = %s
    """, (tenant_id,))

    rent = float(cursor.fetchone()[0])

    for month, year in payment_months:

        status = random.choice(
            payment_statuses
        )

        amount = rent

        if status == "Partially Paid":
            amount = rent * random.uniform(
                0.4,
                0.8
            )

        late_fee = 0

        if status == "Overdue":
            late_fee = random.randint(
                500,
                1500
            )

        cursor.execute("""
            INSERT INTO payments
            (
                tenant_id,
                payment_month,
                payment_year,
                amount,
                payment_date,
                payment_status,
                late_fee
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            tenant_id,
            month,
            year,
            round(amount, 2),
            fake.date_between(
                start_date="-12M",
                end_date="today"
            ),
            status,
            late_fee
        ))

conn.commit()

print("Payments inserted")



expense_categories = [
    "Electricity",
    "Water",
    "Internet",
    "Cleaning",
    "Security",
    "Repairs",
    "Maintenance"
]

for _ in range(150):

    cursor.execute("""
        INSERT INTO expenses
        (
            property_id,
            category,
            amount,
            expense_date,
            description
        )
        VALUES (%s,%s,%s,%s,%s)
    """,
    (
        random.choice(property_ids),
        random.choice(expense_categories),
        random.randint(1000,25000),
        fake.date_between(
            start_date="-12M",
            end_date="today"
        ),
        fake.sentence()
    ))

conn.commit()

print("Expenses inserted")


issue_types = [
    "Plumbing",
    "Electrical",
    "WiFi",
    "AC Repair",
    "Furniture",
    "Painting"
]

statuses = [
    "Open",
    "In Progress",
    "Resolved",
    "Closed"
]

priorities = [
    "Low",
    "Medium",
    "High",
    "Critical"
]

for _ in range(100):

    cursor.execute("""
        INSERT INTO maintenance_requests
        (
            tenant_id,
            room_id,
            issue_type,
            description,
            request_date,
            status,
            priority,
            estimated_cost
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
    """,
    (
        random.choice(tenant_ids),
        random.choice(room_ids),
        random.choice(issue_types),
        fake.sentence(),
        fake.date_between(
            start_date="-12M",
            end_date="today"
        ),
        random.choice(statuses),
        random.choice(priorities),
        random.randint(500,15000)
    ))

conn.commit()

print("Maintenance Requests inserted")


cursor.close()
conn.close()

print("Sample data generation completed successfully")