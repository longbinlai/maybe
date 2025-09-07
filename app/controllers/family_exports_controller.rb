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
        # Ensure URL options are set for this request
        set_active_storage_url_options
        
        # Generate a signed URL for direct download from Active Storage
        # This provides the best download experience with accurate progress bars
        url = @export.export_file.url(
          disposition: "attachment",
          filename: @export.filename
        )
        
        redirect_to url, allow_other_host: true
      rescue ActiveStorage::FileNotFoundError
        # File doesn't exist, mark export as failed and show error
        @export.update!(status: :failed)
        redirect_to settings_profile_path, alert: "Export file not found. Please create a new export."
      rescue => e
        # Handle any other errors
        Rails.logger.error "Export download failed: #{e.message}"
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

    def set_active_storage_url_options
      host = ENV["APP_DOMAIN"].presence || request.host_with_port
      protocol = request.ssl? ? 'https' : 'http'
      
      ActiveStorage::Current.url_options = { 
        host: host,
        protocol: protocol
      }
    end
end
