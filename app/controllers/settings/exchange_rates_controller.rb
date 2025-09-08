require 'set'

class Settings::ExchangeRatesController < ApplicationController
  layout "settings"

  def index
    # 使用 DISTINCT ON 获取每个货币对的最新汇率记录
    @exchange_rates = ExchangeRate.select('DISTINCT ON (from_currency, to_currency) *')
                                  .order(:from_currency, :to_currency, date: :desc)
    
    @supported_currencies = load_supported_currencies
    
    # 加载后备汇率
    all_fallback_rates = load_fallback_rates
    
    # 获取数据库中已存在的货币对
    existing_pairs = Set.new(@exchange_rates.map { |rate| "#{rate.from_currency}-#{rate.to_currency}" })
    
    # 过滤掉数据库中已存在的货币对
    @fallback_rates = {}
    all_fallback_rates.each do |from_currency, rates|
      filtered_rates = {}
      rates.each do |to_currency, rate|
        pair_key = "#{from_currency}-#{to_currency}"
        unless existing_pairs.include?(pair_key)
          filtered_rates[to_currency] = rate
        end
      end
      @fallback_rates[from_currency] = filtered_rates unless filtered_rates.empty?
    end
  end

  def create
    @exchange_rate = ExchangeRate.new(exchange_rate_params)
    
    if @exchange_rate.save
      # Update cache when manually creating rates
      ExchangeRate.update_rate_cache(
        from: @exchange_rate.from_currency, 
        to: @exchange_rate.to_currency, 
        rate: @exchange_rate
      )
      redirect_to settings_exchange_rates_path, notice: t(".success")
    else
      redirect_to settings_exchange_rates_path, alert: t(".error")
    end
  end

  def destroy
    @exchange_rate = ExchangeRate.find(params[:id])
    from_currency = @exchange_rate.from_currency
    to_currency = @exchange_rate.to_currency
    
    @exchange_rate.destroy
    
    # Clear cache when deleting rates
    ExchangeRate.clear_rate_cache(from: from_currency, to: to_currency)
    
    redirect_to settings_exchange_rates_path, notice: t(".deleted")
  end

  def fetch_rate
    from_currency = params[:from_currency]
    to_currency = params[:to_currency]
    date = params[:date]&.to_date || Date.current
    
    if from_currency.blank? || to_currency.blank?
      render json: { error: "缺少货币参数" }, status: :bad_request
      return
    end
    
    if from_currency == to_currency
      render json: { error: "源货币和目标货币不能相同" }, status: :bad_request
      return
    end
    
    begin
      # 直接使用欧洲央行API
      ecb_provider = Provider::EuropeanCentralBank.new
      response = ecb_provider.fetch_exchange_rate(from: from_currency, to: to_currency, date: date)
      
      if response.success?
        rate_data = response.data
        render json: { 
          success: true, 
          rate: rate_data.rate.to_f.round(6),
          from: rate_data.from,
          to: rate_data.to,
          date: rate_data.date.strftime("%Y-%m-%d")
        }
      else
        render json: { 
          error: "无法获取汇率：#{response.error || '提供商返回错误'}" 
        }, status: :service_unavailable
      end
    rescue => e
      Rails.logger.error "Failed to fetch rate #{from_currency} -> #{to_currency}: #{e.message}"
      render json: { 
        error: "获取汇率时发生错误：#{e.message}" 
      }, status: :internal_server_error
    end
  end

  def sync_current_rates
    success_count = 0
    error_count = 0

    # 获取需要更新的货币对：数据库中已存在的汇率记录
    existing_pairs = Set.new(ExchangeRate.select(:from_currency, :to_currency).distinct.map { |rate| 
      [rate.from_currency, rate.to_currency] 
    })
    
    # 添加fallback配置中的货币对
    fallback_rates = load_fallback_rates
    fallback_rates.each do |from_currency, rates|
      rates.each do |to_currency, _rate|
        existing_pairs.add([from_currency.upcase, to_currency.upcase])
      end
    end

    existing_pairs.each do |from_currency, to_currency|
      begin
        # 使用与fetch_rate相同的逻辑获取汇率
        ecb_provider = Provider::EuropeanCentralBank.new
        response = ecb_provider.fetch_exchange_rate(
          from: from_currency, 
          to: to_currency, 
          date: Date.current
        )
        
        if response.success?
          rate_data = response.data
          # 创建或更新汇率记录
          exchange_rate = ExchangeRate.find_or_initialize_by(
            from_currency: rate_data.from,
            to_currency: rate_data.to,
            date: rate_data.date
          )
          exchange_rate.rate = rate_data.rate
          
          if exchange_rate.save
            success_count += 1
            # Update cache when manually syncing rates
            ExchangeRate.update_rate_cache(
              from: exchange_rate.from_currency, 
              to: exchange_rate.to_currency, 
              rate: exchange_rate
            )
          else
            error_count += 1
            Rails.logger.error "Failed to save rate #{from_currency} -> #{to_currency}: #{exchange_rate.errors.full_messages.join(', ')}"
          end
        else
          error_count += 1
          Rails.logger.error "Failed to fetch rate #{from_currency} -> #{to_currency}: #{response.error || 'Provider returned error'}"
        end
      rescue => e
        error_count += 1
        Rails.logger.error "Failed to fetch rate #{from_currency} -> #{to_currency}: #{e.message}"
      end
    end

    if error_count == 0
      redirect_to settings_exchange_rates_path, notice: t(".sync_success", count: success_count)
    else
      redirect_to settings_exchange_rates_path, 
                  alert: t(".sync_partial", success: success_count, errors: error_count)
    end
  end

  private

  def exchange_rate_params
    params.require(:exchange_rate).permit(:from_currency, :to_currency, :rate, :date)
  end

  def load_supported_currencies
    # 从currencies.yml加载支持的货币
    YAML.load_file(Rails.root.join('config', 'currencies.yml')).keys.map(&:upcase)
  end

  def load_fallback_rates
    # 从currency_fallbacks.yml加载后备汇率
    YAML.load_file(Rails.root.join('config', 'currency_fallbacks.yml'))
  end
end
