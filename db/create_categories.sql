-- 创建默认分类数据的SQL语句（中文版）
-- 自动获取第一个family的ID，支持删除原有分类并重新创建

-- 使用变量存储family_id
DO $$
DECLARE
    family_id_var UUID;
    existing_count INTEGER;
BEGIN
    -- 获取第一个family的ID
    SELECT id INTO family_id_var FROM families LIMIT 1;
    
    -- 如果没有family，退出
    IF family_id_var IS NULL THEN
        RAISE NOTICE 'No family found. Please create a family first.';
        RETURN;
    END IF;
    
    -- 检查是否已经有分类数据
    SELECT COUNT(*) INTO existing_count FROM categories WHERE family_id = family_id_var;
    
    -- 如果有现有分类，询问是否要删除并重新创建
    IF existing_count > 0 THEN
        RAISE NOTICE 'Found % existing categories for this family. Deleting them and recreating with Chinese names...', existing_count;
        
        -- 删除现有分类（先删除与交易的关联）
        UPDATE transactions SET category_id = NULL 
        WHERE category_id IN (SELECT id FROM categories WHERE family_id = family_id_var);
        
        -- 删除现有分类
        DELETE FROM categories WHERE family_id = family_id_var;
        
        RAISE NOTICE 'Deleted % existing categories.', existing_count;
    END IF;
    
    -- 插入收入分类（中文）
    INSERT INTO categories (name, classification, color, lucide_icon, family_id, created_at, updated_at) VALUES
    ('工资', 'income', '#4da568', 'circle-dollar-sign', family_id_var, NOW(), NOW()),
    ('投资收入', 'income', '#4da568', 'trending-up', family_id_var, NOW(), NOW()),
    ('自由职业', 'income', '#4da568', 'briefcase', family_id_var, NOW(), NOW()),
    ('商业收入', 'income', '#4da568', 'building', family_id_var, NOW(), NOW()),
    ('其他收入', 'income', '#4da568', 'plus-circle', family_id_var, NOW(), NOW()),
    
    -- 插入支出分类（中文）
    ('餐饮', 'expense', '#eb5429', 'utensils', family_id_var, NOW(), NOW()),
    ('日用品', 'expense', '#eb5429', 'shopping-basket', family_id_var, NOW(), NOW()),
    ('购物', 'expense', '#e99537', 'shopping-cart', family_id_var, NOW(), NOW()),
    ('交通', 'expense', '#df4e92', 'bus', family_id_var, NOW(), NOW()),
    ('娱乐', 'expense', '#df4e92', 'drama', family_id_var, NOW(), NOW()),
    ('房租水电', 'expense', '#db5a54', 'house', family_id_var, NOW(), NOW()),
    ('医疗保健', 'expense', '#4da568', 'pill', family_id_var, NOW(), NOW()),
    ('教育', 'expense', '#6471eb', 'graduation-cap', family_id_var, NOW(), NOW()),
    ('保险', 'expense', '#6471eb', 'shield', family_id_var, NOW(), NOW()),
    ('旅行', 'expense', '#df4e92', 'plane', family_id_var, NOW(), NOW()),
    ('个人护理', 'expense', '#c44fe9', 'user', family_id_var, NOW(), NOW()),
    ('礼品捐赠', 'expense', '#61c9ea', 'hand-helping', family_id_var, NOW(), NOW()),
    ('服务', 'expense', '#4da568', 'briefcase', family_id_var, NOW(), NOW()),
    ('账单费用', 'expense', '#db5a54', 'credit-card', family_id_var, NOW(), NOW()),
    ('其他支出', 'expense', '#805dee', 'circle', family_id_var, NOW(), NOW());
    
    RAISE NOTICE 'Categories created successfully for family_id: %. Total categories: 20', family_id_var;
END $$;
