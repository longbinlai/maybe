# The shape of data expected by `confirm_dialog_controller.js` to override the
# default browser confirm API via Turbo.
class CustomConfirm
  class << self
    def for_resource_deletion(resource_name, high_severity: false)
      translated_resource = translate_resource_name(resource_name)
      
      new(
        destructive: true,
        high_severity: high_severity,
        title: I18n.t("shared.custom_confirm.delete_title", resource: translated_resource),
        body: I18n.t("shared.custom_confirm.delete_body", resource: translated_resource.downcase),
        btn_text: I18n.t("shared.custom_confirm.delete_button", resource: translated_resource)
      )
    end
    
    private
    
    def translate_resource_name(resource_name)
      # Try to find a specific translation for the resource
      key = "shared.custom_confirm.resources.#{resource_name.downcase.gsub(' ', '_')}"
      translated = I18n.t(key, default: nil)
      
      # If no specific translation found, use the original but titleized
      translated || resource_name.titleize
    end
  end

  def initialize(title: default_title, body: default_body, btn_text: default_btn_text, destructive: false, high_severity: false)
    @title = title
    @body = body
    @btn_text = btn_text
    @btn_variant = derive_btn_variant(destructive, high_severity)
  end

  def to_data_attribute
    {
      title: title,
      body: body,
      confirmText: btn_text,
      variant: btn_variant
    }
  end

  private
    attr_reader :title, :body, :btn_text, :btn_variant

    def derive_btn_variant(destructive, high_severity)
      return "primary" unless destructive
      high_severity ? "destructive" : "outline-destructive"
    end

    def default_title
      I18n.t("shared.custom_confirm.default_title")
    end

    def default_body
      I18n.t("shared.custom_confirm.default_body")
    end

    def default_btn_text
      I18n.t("shared.custom_confirm.default_button")
    end
end
