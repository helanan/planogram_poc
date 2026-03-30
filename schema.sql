-- Run this in your Supabase SQL editor to create the required tables.

create table if not exists products (
    id          bigint primary key generated always as identity,
    name        text        not null,
    sku         text        unique,
    width_in    numeric     not null,  -- product width in inches
    height_in   numeric     not null   -- product height in inches
);

create table if not exists shelf_layout (
    id          bigint primary key generated always as identity,
    product_id  bigint      references products(id) on delete cascade,
    x_pos       numeric     not null,  -- left edge position in inches
    y_pos       numeric     not null   -- bottom edge position in inches
);

-- Sample data
insert into products (name, sku, width_in, height_in) values
    ('Dog Food 40lb',   'DF-40',  8, 12),
    ('Horse Feed 50lb', 'HF-50', 10, 14),
    ('Work Gloves L',   'WG-L',   4,  6),
    ('Boot Spray 12oz', 'BS-12',  3,  7);

insert into shelf_layout (product_id, x_pos, y_pos)
select id, 0,  0 from products where sku = 'Dog Food 40lb'   limit 1;
insert into shelf_layout (product_id, x_pos, y_pos)
select id, 10, 0 from products where sku = 'Horse Feed 50lb' limit 1;
insert into shelf_layout (product_id, x_pos, y_pos)
select id, 22, 0 from products where sku = 'Work Gloves L'   limit 1;
insert into shelf_layout (product_id, x_pos, y_pos)
select id, 28, 0 from products where sku = 'Boot Spray 12oz' limit 1;
