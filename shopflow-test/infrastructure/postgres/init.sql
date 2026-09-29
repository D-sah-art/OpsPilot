-- ShopFlow Initial Schema and Seed Data

CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(64) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(32) DEFAULT 'customer',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    id VARCHAR(64) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(64) NOT NULL,
    price NUMERIC(10, 2) NOT NULL,
    rating NUMERIC(3, 2) DEFAULT 4.5,
    review_count INTEGER DEFAULT 120,
    stock INTEGER NOT NULL DEFAULT 50,
    image_url TEXT NOT NULL,
    badge VARCHAR(64),
    specs JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orders (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    user_email VARCHAR(255) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'CONFIRMED',
    subtotal NUMERIC(10, 2) NOT NULL,
    tax NUMERIC(10, 2) NOT NULL,
    shipping NUMERIC(10, 2) NOT NULL,
    total NUMERIC(10, 2) NOT NULL,
    shipping_address JSONB NOT NULL,
    payment_method VARCHAR(64) NOT NULL DEFAULT 'Credit Card (Simulated)',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS order_items (
    id VARCHAR(64) PRIMARY KEY,
    order_id VARCHAR(64) REFERENCES orders(id) ON DELETE CASCADE,
    product_id VARCHAR(64) NOT NULL,
    product_title VARCHAR(255) NOT NULL,
    price NUMERIC(10, 2) NOT NULL,
    quantity INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Seed Demo Users (passwords: 'demo123')
INSERT INTO users (id, email, password_hash, full_name, role) VALUES
('usr_alex_01', 'alex@shopflow.dev', '$2b$12$e9Qq0.v3pQW8lG5pA/3X5eQoGj.n.sD5Xh4Kk6Yn.oJ8l.xM.3C2e', 'Alex Rivera', 'customer'),
('usr_sarah_02', 'sarah@shopflow.dev', '$2b$12$e9Qq0.v3pQW8lG5pA/3X5eQoGj.n.sD5Xh4Kk6Yn.oJ8l.xM.3C2e', 'Sarah Chen', 'customer'),
('usr_admin_03', 'ops@shopflow.dev', '$2b$12$e9Qq0.v3pQW8lG5pA/3X5eQoGj.n.sD5Xh4Kk6Yn.oJ8l.xM.3C2e', 'DevOps Lead', 'admin')
ON CONFLICT (id) DO NOTHING;

-- Seed Products across diverse e-commerce categories
INSERT INTO products (id, title, description, category, price, rating, review_count, stock, image_url, badge, specs) VALUES
('prod_01', 'ProFlow Noise-Canceling Headphones', 'Premium wireless acoustic headphones with adaptive ANC, 40-hour battery life, and spatial audio.', 'Electronics', 299.99, 4.9, 342, 45, 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600&auto=format&fit=crop&q=80', 'Best Seller', '{"Battery": "40 hrs", "Connectivity": "Bluetooth 5.3", "Weight": "250g", "ANC": "Adaptive"}'),
('prod_02', 'AeroMechanical RGB Keyboard', 'Hot-swappable tactile mechanical keyboard with PBT keycaps, per-key RGB, and wireless dual-mode.', 'Electronics', 149.50, 4.8, 189, 28, 'https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=600&auto=format&fit=crop&q=80', 'Popular', '{"Switches": "Tactile Brown", "Layout": "75%", "RGB": "16.8M colors", "Connection": "2.4GHz / USB-C"}'),
('prod_03', 'UltraPrecision Ergonomic Mouse', 'High-accuracy wireless mouse with magnetic scroll wheel, ergonomic palm support, and fast charging.', 'Electronics', 89.00, 4.7, 512, 60, 'https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?w=600&auto=format&fit=crop&q=80', 'Staff Pick', '{"DPI": "16000 DPI", "Battery": "70 days", "Buttons": "7 programmable"}'),
('prod_04', 'Studio UltraWide 4K Monitor 34"', 'Curved IPS 144Hz HDR600 display with 99% DCI-P3 color accuracy and 90W USB-C power delivery.', 'Electronics', 649.99, 4.9, 98, 15, 'https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=600&auto=format&fit=crop&q=80', 'Featured', '{"Resolution": "3440 x 1440", "Refresh Rate": "144Hz", "Panel": "Fast IPS", "Ports": "USB-C, HDMI 2.1, DP 1.4"}'),
('prod_05', 'Merino Wool Minimalist Hoodie', 'Engineered thermal regulation merino wool blend pullover designed for comfort and durability.', 'Apparel', 115.00, 4.6, 215, 80, 'https://images.unsplash.com/photo-1556905055-8f358a7a47b2?w=600&auto=format&fit=crop&q=80', 'Eco-Friendly', '{"Material": "80% Merino Wool, 20% Recycled Poly", "Fit": "Athletic", "Care": "Machine wash cold"}'),
('prod_06', 'All-Weather Tech Waterproof Parka', '3-layer breathable waterproof membrane jacket with stormproof seams and thermal interior lining.', 'Apparel', 240.00, 4.8, 164, 32, 'https://images.unsplash.com/photo-1548883354-7622d03aca27?w=600&auto=format&fit=crop&q=80', 'New Arrival', '{"Waterproof Rating": "20,000mm", "Breathability": "15,000g", "Pockets": "6 sealed"}'),
('prod_07', 'Artisan Pour-Over Coffee Station', 'Borosilicate glass dripper with solid walnut stand, precision gooseneck kettle, and digital scale.', 'Home & Living', 125.00, 4.9, 420, 50, 'https://images.unsplash.com/photo-1517668808822-9ebb02f2a0e6?w=600&auto=format&fit=crop&q=80', 'Bestseller', '{"Capacity": "800ml", "Material": "Walnut & Glass", "Kettle": "1.0L Temperature Control"}'),
('prod_08', 'Ergonomic Mesh Lumbar Desk Chair', 'Dynamic lumbar support, 4D adjustable armrests, breathable mesh back, and aluminum wheelbase.', 'Home & Living', 380.00, 4.7, 310, 22, 'https://images.unsplash.com/photo-1580481077194-e4359cf9c6dc?w=600&auto=format&fit=crop&q=80', 'Top Rated', '{"Weight Capacity": "300 lbs", "Adjustability": "4D Armrests, Lumbar, Height", "Warranty": "5 Years"}'),
('prod_09', 'Full-Grain Leather Everyday Briefcase', 'Handcrafted vegetable-tanned leather briefcase with padded laptop sleeve and brass hardware.', 'Accessories', 195.00, 4.9, 140, 25, 'https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=600&auto=format&fit=crop&q=80', 'Handmade', '{"Fits Laptop": "Up to 16-inch", "Leather": "Full-grain Italian", "Hardware": "Solid Brass"}'),
('prod_10', 'Titanium Modular Everyday Pen', 'Precision CNC-machined Grade 5 titanium body with Schmidt EasyFlow 9000 refill cartridge.', 'Accessories', 65.00, 4.8, 275, 110, 'https://images.unsplash.com/photo-1583485088034-697b5bc54ccd?w=600&auto=format&fit=crop&q=80', 'Trending', '{"Material": "Grade 5 Titanium", "Refill": "Schmidt 9000", "Length": "135mm"}'),
('prod_11', 'Smart Ambient Light Bar 2-Pack', 'Syncs with monitor audio and screen colors, 16 million colors, voice control, and preset scenes.', 'Electronics', 79.99, 4.5, 380, 70, 'https://images.unsplash.com/photo-1507473885765-e6ed057f782c?w=600&auto=format&fit=crop&q=80', 'Smart Tech', '{"Connectivity": "WiFi 2.4GHz + BT", "Lumens": "500lm each", "Voice Support": "Alexa & Google"}'),
('prod_12', 'Matte Ceramic Desk Organizer Tray', 'Minimalist dual-compartment heavy stoneware tray for organizing cables, watches, and stationery.', 'Home & Living', 35.00, 4.6, 95, 120, 'https://images.unsplash.com/photo-1544816155-12df9643f363?w=600&auto=format&fit=crop&q=80', 'Essential', '{"Finish": "Matte Glazed", "Dimensions": "22 x 12 x 2.5 cm", "Weight": "450g"}')
ON CONFLICT (id) DO NOTHING;

-- Seed Sample Prior Orders
INSERT INTO orders (id, user_id, user_email, status, subtotal, tax, shipping, total, shipping_address, payment_method, created_at) VALUES
('ord_1001', 'usr_alex_01', 'alex@shopflow.dev', 'DELIVERED', 299.99, 24.00, 0.00, 323.99, '{"street": "742 Evergreen Terrace", "city": "Springfield", "state": "OR", "zip": "97477", "country": "USA"}', 'Credit Card (**** 4242)', CURRENT_TIMESTAMP - INTERVAL '3 days'),
('ord_1002', 'usr_alex_01', 'alex@shopflow.dev', 'SHIPPED', 149.50, 11.96, 0.00, 161.46, '{"street": "742 Evergreen Terrace", "city": "Springfield", "state": "OR", "zip": "97477", "country": "USA"}', 'Credit Card (**** 4242)', CURRENT_TIMESTAMP - INTERVAL '1 day')
ON CONFLICT (id) DO NOTHING;

INSERT INTO order_items (id, order_id, product_id, product_title, price, quantity) VALUES
('itm_01', 'ord_1001', 'prod_01', 'ProFlow Noise-Canceling Headphones', 299.99, 1),
('itm_02', 'ord_1002', 'prod_02', 'AeroMechanical RGB Keyboard', 149.50, 1)
ON CONFLICT (id) DO NOTHING;
