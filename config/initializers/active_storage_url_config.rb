# Configure Active Storage URL options once at startup
Rails.application.configure do
  config.after_initialize do
    # Set default URL options for Active Storage
    # This runs once at startup, not on every request
    default_host = ENV["APP_DOMAIN"].presence || "localhost:3000"
    default_protocol = if Rails.env.production? && !default_host.include?("localhost")
      ENV["RAILS_FORCE_SSL"] == "true" ? "https" : "http"
    else
      "http"
    end
    
    ActiveStorage::Current.url_options = {
      host: default_host,
      protocol: default_protocol
    }
    
    Rails.logger.info "Active Storage URL options configured: #{ActiveStorage::Current.url_options}"
  end
end
