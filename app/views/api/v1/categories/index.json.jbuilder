json.categories @categories do |category|
  json.id category.id
  json.name category.name
  json.classification category.classification
  json.parent_id category.parent_id
end
