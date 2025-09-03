module Breadcrumbable
  extend ActiveSupport::Concern

  included do
    before_action :set_breadcrumbs
  end

  private
    # The default, unless specific controller or action explicitly overrides
    def set_breadcrumbs
      @breadcrumbs = [ [ t("shared.breadcrumbs.home"), root_path ], [ t("shared.breadcrumbs.#{controller_name}"), nil ] ]
    end
end
