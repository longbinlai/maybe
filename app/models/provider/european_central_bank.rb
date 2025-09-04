class Provider::EuropeanCentralBank
  include Provider::ExchangeRateConcept
  
  # 欧洲央行提供完全免费的汇率数据
  CURRENT_RATES_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
  HISTORICAL_RATES_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml" # 最近90天
  
  def initialize
    # 无需API密钥，完全免费
  end
  
  def fetch_exchange_rate(from:, to:, date: Date.current)
    # ECB以EUR为基础货币
    if from == "EUR"
      fetch_eur_to_currency(to, date)
    elsif to == "EUR"
      fetch_currency_to_eur(from, date)
    else
      # 通过EUR进行间接转换: from -> EUR -> to
      fetch_cross_rate(from, to, date)
    end
  rescue => e
    Rails.logger.error("ECB API error: #{e.message}")
    OpenStruct.new(success?: false, error: e.message)
  end
  
  private
  
  def fetch_eur_to_currency(to_currency, date)
    rates = fetch_rates_for_date(date)
    
    if rates[to_currency]
      rate_data = OpenStruct.new(
        from: "EUR",
        to: to_currency,
        date: date,
        rate: BigDecimal(rates[to_currency].to_s)
      )
      OpenStruct.new(success?: true, data: rate_data)
    else
      OpenStruct.new(success?: false, error: "Currency #{to_currency} not supported by ECB")
    end
  end
  
  def fetch_currency_to_eur(from_currency, date)
    rates = fetch_rates_for_date(date)
    
    if rates[from_currency]
      # 反向计算：1 / (EUR -> currency) = currency -> EUR
      eur_rate = BigDecimal("1") / BigDecimal(rates[from_currency].to_s)
      
      rate_data = OpenStruct.new(
        from: from_currency,
        to: "EUR",
        date: date,
        rate: eur_rate
      )
      OpenStruct.new(success?: true, data: rate_data)
    else
      OpenStruct.new(success?: false, error: "Currency #{from_currency} not supported by ECB")
    end
  end
  
  def fetch_cross_rate(from_currency, to_currency, date)
    rates = fetch_rates_for_date(date)
    
    from_rate = rates[from_currency]
    to_rate = rates[to_currency]
    
    if from_rate && to_rate
      # 交叉汇率计算: (from -> EUR) * (EUR -> to) = from -> to
      # from -> EUR = 1 / from_rate
      # EUR -> to = to_rate
      # from -> to = (1 / from_rate) * to_rate = to_rate / from_rate
      cross_rate = BigDecimal(to_rate.to_s) / BigDecimal(from_rate.to_s)
      
      rate_data = OpenStruct.new(
        from: from_currency,
        to: to_currency,
        date: date,
        rate: cross_rate
      )
      OpenStruct.new(success?: true, data: rate_data)
    else
      missing_currencies = []
      missing_currencies << from_currency unless from_rate
      missing_currencies << to_currency unless to_rate
      OpenStruct.new(success?: false, error: "Currencies not supported by ECB: #{missing_currencies.join(', ')}")
    end
  end
  
  def fetch_rates_for_date(date)
    xml_url = if date == Date.current || date >= Date.current - 1.day
      CURRENT_RATES_URL
    elsif date >= Date.current - 90.days
      HISTORICAL_RATES_URL
    else
      # ECB免费API只提供最近90天的历史数据
      Rails.logger.warn("ECB free API only provides 90 days of historical data. Requested: #{date}")
      return {}
    end
    
    uri = URI(xml_url)
    response = Net::HTTP.get_response(uri)
    
    if response.code == "200"
      parse_ecb_xml(response.body, date)
    else
      Rails.logger.error("ECB API HTTP error: #{response.code}")
      {}
    end
  end
  
  def parse_ecb_xml(xml_content, target_date)
    require 'nokogiri'
    
    doc = Nokogiri::XML(xml_content)
    rates = {}
    
    # 查找指定日期的汇率
    cube_time = doc.xpath("//xmlns:Cube[@time='#{target_date.strftime('%Y-%m-%d')}']").first
    
    # 如果找不到确切日期，使用最新的汇率
    cube_time ||= doc.xpath("//xmlns:Cube[@time]").first
    
    if cube_time
      # 解析该日期下的所有汇率
      cube_time.xpath(".//xmlns:Cube[@currency and @rate]").each do |cube|
        currency = cube['currency']
        rate = cube['rate']
        rates[currency] = rate.to_f
      end
    end
    
    rates
  end
end
