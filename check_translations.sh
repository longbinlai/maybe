#!/bin/bash

# 检查中文翻译文件数量
echo "中文翻译文件统计："
echo "==================="

# Views翻译文件
views_count=$(find config/locales/views -name "zh-CN.yml" | wc -l)
echo "Views翻译文件: $views_count 个"

# Models翻译文件  
models_count=$(find config/locales/models -name "zh-CN.yml" | wc -l)
echo "Models翻译文件: $models_count 个"

# Mailers翻译文件
mailers_count=$(find config/locales/mailers -name "zh-CN.yml" 2>/dev/null | wc -l)
echo "Mailers翻译文件: $mailers_count 个"

# 默认翻译文件
defaults_count=$(find config/locales/defaults -name "zh-CN.yml" | wc -l)
echo "Defaults翻译文件: $defaults_count 个"

echo ""
echo "总计: $((views_count + models_count + mailers_count + defaults_count)) 个中文翻译文件"

echo ""
echo "对应的英文翻译文件："
echo "==================="

# Views英文翻译文件
en_views_count=$(find config/locales/views -name "en.yml" | wc -l)
echo "Views英文翻译文件: $en_views_count 个"

# Models英文翻译文件
en_models_count=$(find config/locales/models -name "en.yml" | wc -l)
echo "Models英文翻译文件: $en_models_count 个"

echo ""
echo "翻译覆盖率："
echo "============"
echo "Views: $views_count/$en_views_count ($(( views_count * 100 / en_views_count ))%)"
echo "Models: $models_count/$en_models_count ($(( models_count * 100 / en_models_count ))%)"
