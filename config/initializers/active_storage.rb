Rails.application.configure do
  config.after_initialize do
    host = ENV["APP_DOMAIN"].presence || "localhost:3000"
    
    ActiveStorage::Current.url_options = { 
      host: host,
      protocol: (Rails.application.config.force_ssl && !host.include?("localhost")) ? 'https' : 'http'
    }
    
    Rails.logger.info "Active Storage URL options set: #{ActiveStorage::Current.url_options.inspect}"
  end
end
