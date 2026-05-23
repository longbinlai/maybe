class Api::V1::TagsController < Api::V1::BaseController
  before_action :ensure_read_scope

  def index
    @tags = current_resource_owner.family.tags.order(:name)
    render :index
  end

  private
    def ensure_read_scope
      authorize_scope!(:read)
    end
end
