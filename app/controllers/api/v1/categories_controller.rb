class Api::V1::CategoriesController < Api::V1::BaseController
  before_action :ensure_read_scope

  def index
    @categories = current_resource_owner.family.categories.order(:name)
    render :index
  end

  private
    def ensure_read_scope
      authorize_scope!(:read)
    end
end
