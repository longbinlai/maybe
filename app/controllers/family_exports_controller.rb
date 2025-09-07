class FamilyExportsController < ApplicationController
  include StreamExtensions

  before_action :require_admin
  before_action :set_export, only: [ :download, :destroy ]

  def new
    # Modal view for initiating export
  end

  def create
    @export = Current.family.family_exports.create!
    FamilyDataExportJob.perform_later(@export)

    respond_to do |format|
      format.html { redirect_to settings_profile_path, notice: "Export started. You'll be able to download it shortly." }
      format.turbo_stream {
        stream_redirect_to settings_profile_path, notice: "Export started. You'll be able to download it shortly."
      }
    end
  end

  def index
    @exports = Current.family.family_exports.ordered.limit(10)
    render layout: false # For turbo frame
  end

  def download
    if @export.downloadable?
      begin
        # Stream the file directly instead of redirecting to Active Storage URL
        send_data @export.export_file.download, 
                  filename: @export.filename,
                  type: @export.export_file.content_type,
                  disposition: 'attachment'
      rescue ActiveStorage::FileNotFoundError
        # File doesn't exist, mark export as failed and show error
        @export.update!(status: :failed)
        redirect_to settings_profile_path, alert: "Export file not found. Please create a new export."
      end
    else
      redirect_to settings_profile_path, alert: "Export not ready for download"
    end
  end

  def destroy
    @export.destroy!
    
    respond_to do |format|
      format.html { redirect_to settings_profile_path, notice: "Export deleted successfully." }
      format.turbo_stream {
        stream_redirect_to settings_profile_path, notice: "Export deleted successfully."
      }
    end
  end

  private

    def set_export
      @export = Current.family.family_exports.find(params[:id])
    end

    def require_admin
      unless Current.user.admin?
        redirect_to root_path, alert: "Access denied"
      end
    end
end
