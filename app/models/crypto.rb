class Crypto < ApplicationRecord
  include Accountable

  class << self
    def color
      "#737373"
    end

    def classification
      "asset"
    end

    def icon
      "bitcoin"
    end

    def display_name
      I18n.t("activerecord.models.account/crypto", default: "Crypto")
    end
  end
end
