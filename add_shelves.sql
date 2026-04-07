-- Add more products
insert into products (name, sku, width_in, height_in) values
    ('Cat Food 16lb',      'CF-16',  7,  10),
    ('Bird Seed 20lb',     'BS-20',  9,  13),
    ('Chicken Feed 50lb',  'CHF-50', 11, 15),
    ('Fence Pliers',       'FP-01',  3,   8),
    ('Leather Belt',       'LB-M',   4,   5),
    ('Rope 50ft',          'RP-50',  6,   6),
    ('Motor Oil QT',       'MO-QT',  3,   8),
    ('Hay Net',            'HN-01',  8,  10),
    ('Salt Block 50lb',    'SB-50',  8,  10);

-- Shelf 2 (y_pos = 16)
insert into shelf_layout (product_id, x_pos, y_pos)
select id,  0, 16 from products where sku = 'CF-16'   limit 1;
insert into shelf_layout (product_id, x_pos, y_pos)
select id,  9, 16 from products where sku = 'BS-20'   limit 1;
insert into shelf_layout (product_id, x_pos, y_pos)
select id, 20, 16 from products where sku = 'CHF-50'  limit 1;
insert into shelf_layout (product_id, x_pos, y_pos)
select id, 33, 16 from products where sku = 'FP-01'   limit 1;
insert into shelf_layout (product_id, x_pos, y_pos)
select id, 38, 16 from products where sku = 'LB-M'    limit 1;

-- Shelf 3 (y_pos = 32)
insert into shelf_layout (product_id, x_pos, y_pos)
select id,  0, 32 from products where sku = 'RP-50'   limit 1;
insert into shelf_layout (product_id, x_pos, y_pos)
select id,  8, 32 from products where sku = 'MO-QT'   limit 1;
insert into shelf_layout (product_id, x_pos, y_pos)
select id, 13, 32 from products where sku = 'HN-01'   limit 1;
insert into shelf_layout (product_id, x_pos, y_pos)
select id, 23, 32 from products where sku = 'SB-50'   limit 1;
