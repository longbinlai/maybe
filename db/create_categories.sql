-- 创建默认分类数据的SQL语句
-- 自动获取第一个family的ID

-- 使用变量存储family_id
DO $$
DECLARE
    family_id_var UUID;
BEGIN
    -- 获取第一个family的ID
    SELECT id INTO family_id_var FROM families LIMIT 1;
    
    -- 如果没有family，退出
    IF family_id_var IS NULL THEN
        RAISE NOTICE 'No family found. Please create a family first.';
        RETURN;
    END IF;
    
    -- 检查是否已经有分类数据
    IF EXISTS (SELECT 1 FROM categories WHERE family_id = family_id_var) THEN
        RAISE NOTICE 'Categories already exist for this family.';
        RETURN;
    END IF;
    
    -- 插入收入分类
    INSERT INTO categories (name, classification, color, lucide_icon, family_id, created_at, updated_at) VALUES
    ('Salary', 'income', '#4da568', 'circle-dollar-sign', family_id_var, NOW(), NOW()),
    ('Investment', 'income', '#4da568', 'trending-up', family_id_var, NOW(), NOW()),
    ('Freelance', 'income', '#4da568', 'briefcase', family_id_var, NOW(), NOW()),
    ('Business', 'income', '#4da568', 'building', family_id_var, NOW(), NOW()),
    ('Other Income', 'income', '#4da568', 'plus-circle', family_id_var, NOW(), NOW()),
    
    -- 插入支出分类
    ('Food & Dining', 'expense', '#eb5429', 'utensils', family_id_var, NOW(), NOW()),
    ('Groceries', 'expense', '#eb5429', 'shopping-basket', family_id_var, NOW(), NOW()),
    ('Shopping', 'expense', '#e99537', 'shopping-cart', family_id_var, NOW(), NOW()),
    ('Transportation', 'expense', '#df4e92', 'bus', family_id_var, NOW(), NOW()),
    ('Entertainment', 'expense', '#df4e92', 'drama', family_id_var, NOW(), NOW()),
    ('Rent & Utilities', 'expense', '#db5a54', 'house', family_id_var, NOW(), NOW()),
    ('Healthcare', 'expense', '#4da568', 'pill', family_id_var, NOW(), NOW()),
    ('Education', 'expense', '#6471eb', 'graduation-cap', family_id_var, NOW(), NOW()),
    ('Insurance', 'expense', '#6471eb', 'shield', family_id_var, NOW(), NOW()),
    ('Travel', 'expense', '#df4e92', 'plane', family_id_var, NOW(), NOW()),
    ('Personal Care', 'expense', '#c44fe9', 'user', family_id_var, NOW(), NOW()),
    ('Gifts & Donations', 'expense', '#61c9ea', 'hand-helping', family_id_var, NOW(), NOW()),
    ('Services', 'expense', '#4da568', 'briefcase', family_id_var, NOW(), NOW()),
    ('Bills & Fees', 'expense', '#db5a54', 'credit-card', family_id_var, NOW(), NOW()),
    ('Other Expenses', 'expense', '#805dee', 'circle', family_id_var, NOW(), NOW());
    
    RAISE NOTICE 'Categories created successfully for family_id: %', family_id_var;
END $$;
