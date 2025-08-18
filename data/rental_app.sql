-- Schema for rental_app (SQLite compatible)
PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS favorites;
DROP TABLE IF EXISTS property_photos;
DROP TABLE IF EXISTS reviews;
DROP TABLE IF EXISTS payments;
DROP TABLE IF EXISTS bookings;
DROP TABLE IF EXISTS properties;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
  user_id INTEGER PRIMARY KEY,
  first_name TEXT,
  last_name TEXT,
  email TEXT UNIQUE,
  phone TEXT,
  role TEXT CHECK(role IN ('landlord','tenant','admin')),
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE properties (
  property_id INTEGER PRIMARY KEY,
  landlord_id INTEGER,
  title TEXT,
  description TEXT,
  property_type TEXT CHECK(property_type IN ('apartment','house','studio','villa')),
  address TEXT,
  city TEXT,
  state TEXT,
  country TEXT,
  bedrooms INTEGER,
  bathrooms INTEGER,
  rent_price REAL,
  status TEXT CHECK(status IN ('available','booked','inactive')),
  listed_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (landlord_id) REFERENCES users(user_id)
);

CREATE TABLE bookings (
  booking_id INTEGER PRIMARY KEY,
  property_id INTEGER,
  tenant_id INTEGER,
  start_date TEXT,
  end_date TEXT,
  status TEXT CHECK(status IN ('pending','confirmed','cancelled','completed')),
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (property_id) REFERENCES properties(property_id),
  FOREIGN KEY (tenant_id) REFERENCES users(user_id)
);

CREATE TABLE payments (
  payment_id INTEGER PRIMARY KEY,
  booking_id INTEGER,
  tenant_id INTEGER,
  amount REAL,
  payment_date TEXT,
  status TEXT CHECK(status IN ('initiated','successful','failed','refunded')),
  method TEXT CHECK(method IN ('credit_card','debit_card','bank_transfer','upi','cash')),
  FOREIGN KEY (booking_id) REFERENCES bookings(booking_id),
  FOREIGN KEY (tenant_id) REFERENCES users(user_id)
);

CREATE TABLE reviews (
  review_id INTEGER PRIMARY KEY,
  property_id INTEGER,
  tenant_id INTEGER,
  rating INTEGER CHECK(rating BETWEEN 1 AND 5),
  comment TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (property_id) REFERENCES properties(property_id),
  FOREIGN KEY (tenant_id) REFERENCES users(user_id)
);

CREATE TABLE property_photos (
  photo_id INTEGER PRIMARY KEY,
  property_id INTEGER,
  photo_url TEXT,
  uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (property_id) REFERENCES properties(property_id)
);

CREATE TABLE favorites (
  tenant_id INTEGER,
  property_id INTEGER,
  added_at TEXT DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (tenant_id, property_id),
  FOREIGN KEY (tenant_id) REFERENCES users(user_id),
  FOREIGN KEY (property_id) REFERENCES properties(property_id)
);

-- Seed users (landlords and tenants)
INSERT INTO users(user_id, first_name, last_name, email, phone, role) VALUES
  (1,'Alice','Landlord','alice.landlord@example.com','+10000000001','landlord'),
  (2,'Bob','Owner','bob.owner@example.com','+10000000002','landlord'),
  (3,'Carol','Tenant','carol.tenant@example.com','+10000001001','tenant'),
  (4,'Dave','Tenant','dave.tenant@example.com','+10000001002','tenant'),
  (5,'Eve','Tenant','eve.tenant@example.com','+10000001003','tenant');

-- Seed properties
INSERT INTO properties(property_id, landlord_id, title, description, property_type, address, city, state, country, bedrooms, bathrooms, rent_price, status)
VALUES
  (101,1,'Cozy Apt Bradford','Central location','apartment','1 High St','Bradford','West Yorkshire','UK',2,1,1800,'available'),
  (102,1,'Spacious House Bradford','Garden and parking','house','2 Park Rd','Bradford','West Yorkshire','UK',3,2,2500,'booked'),
  (103,2,'Modern Studio London','Close to tube','studio','10 Baker St','London','London','UK',1,1,1500,'available'),
  (104,2,'Family House London','Quiet area','house','22 Elm Ave','London','London','UK',4,2,3200,'available'),
  (105,1,'Stylish Apt London','Great view','apartment','99 River Rd','London','London','UK',2,2,2400,'available');

-- Seed bookings
INSERT INTO bookings(booking_id, property_id, tenant_id, start_date, end_date, status) VALUES
  (1001,101,3,'2025-04-05','2025-06-15','completed'),
  (1002,102,4,'2025-05-01','2025-05-31','completed'),
  (1003,103,5,'2025-07-01','2025-07-15','confirmed');

-- Seed payments
INSERT INTO payments(payment_id, booking_id, tenant_id, amount, payment_date, status, method) VALUES
  (2001,1001,3,3600,'2025-05-01','successful','credit_card'),
  (2002,1002,4,2500,'2025-06-01','successful','bank_transfer'),
  (2003,1003,5,1500,'2025-07-02','initiated','upi');

-- Seed reviews
INSERT INTO reviews(review_id, property_id, tenant_id, rating, comment) VALUES
  (3001,101,3,4,'Nice place'),
  (3002,102,4,5,'Great house'),
  (3003,105,5,3,'Average');

-- Photos and favorites (minimal)
INSERT INTO property_photos(photo_id, property_id, photo_url) VALUES
  (4001,101,'/photos/101/1.jpg');

INSERT INTO favorites(tenant_id, property_id) VALUES
  (3,105);
