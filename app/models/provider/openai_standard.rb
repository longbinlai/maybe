class Provider::OpenaiStandard < Provider
  include LlmConcept

  # Subclass so errors caught in this provider are raised as Provider::OpenaiStandard::Error
  Error = Class.new(Provider::Error)

  # Standard OpenAI models
  MODELS = ENV.fetch("OPENAI_MODELS", "gpt-4o-mini,gpt-4o,gpt-4,gpt-3.5-turbo").split(",").map(&:strip)

  def initialize(access_token)
    @client = ::OpenAI::Client.new(
      access_token: access_token,
      uri_base: "https://api.openai.com"
    )
  end

  def supports_model?(model)
    MODELS.include?(model)
  end

  def auto_categorize(transactions: [], user_categories: [])
    with_provider_response do
      raise Error, "Too many transactions to auto-categorize. Max is 25 per request." if transactions.size > 25

      prompt = build_categorization_prompt(transactions, user_categories)
      response = chat_completion(prompt, model: "gpt-4o-mini")
      
      parse_categorization_response(response, transactions)
    end
  end

  def auto_detect_merchants(transactions: [], user_merchants: [])
    with_provider_response do
      raise Error, "Too many transactions to auto-detect merchants. Max is 25 per request." if transactions.size > 25

      prompt = build_merchant_detection_prompt(transactions, user_merchants)
      response = chat_completion(prompt, model: "gpt-4o-mini")
      
      parse_merchant_detection_response(response, transactions)
    end
  end

  def chat_response(prompt, model:, instructions: nil, functions: [], function_results: [], streamer: nil, previous_response_id: nil)
    with_provider_response do
      messages = build_messages(prompt, instructions, function_results)
      tools = build_tools(functions) if functions.any?

      parameters = {
        model: model,
        messages: messages,
        stream: streamer.present?
      }
      
      parameters[:tools] = tools if tools&.any?

      if streamer.present?
        response = @client.chat(parameters: parameters) do |chunk|
          parsed_chunk = parse_stream_chunk(chunk)
          streamer.call(parsed_chunk) if parsed_chunk
        end
        # Return the last complete response from streaming
        build_chat_response_from_stream(response)
      else
        response = @client.chat(parameters: parameters)
        build_chat_response(response)
      end
    end
  end

  private
    attr_reader :client

    def chat_completion(prompt, model:)
      @client.chat(
        parameters: {
          model: model,
          messages: [{ role: "user", content: prompt }],
          temperature: 0.1
        }
      )
    end

    def build_messages(prompt, instructions, function_results)
      messages = []
      
      if instructions.present?
        messages << { role: "system", content: instructions }
      end
      
      messages << { role: "user", content: prompt }
      
      # Add function results if any
      function_results.each do |result|
        messages << {
          role: "tool",
          tool_call_id: result[:call_id],
          content: result[:output].to_json
        }
      end
      
      messages
    end

    def build_tools(functions)
      functions.map do |fn|
        {
          type: "function",
          function: {
            name: fn[:name],
            description: fn[:description],
            parameters: fn[:params_schema]
          }
        }
      end
    end

    def build_chat_response(response)
      message = response.dig("choices", 0, "message")
      
      Provider::LlmConcept::ChatResponse.new(
        id: response["id"],
        model: response["model"],
        messages: [
          Provider::LlmConcept::ChatMessage.new(
            id: response["id"],
            output_text: message["content"] || ""
          )
        ],
        function_requests: extract_function_requests(message)
      )
    end

    def build_chat_response_from_stream(response)
      # This would need to be implemented based on the streaming response format
      # For now, return a basic response
      Provider::LlmConcept::ChatResponse.new(
        id: SecureRandom.uuid,
        model: "gpt-4o-mini",
        messages: [
          Provider::LlmConcept::ChatMessage.new(
            id: SecureRandom.uuid,
            output_text: ""
          )
        ],
        function_requests: []
      )
    end

    def parse_stream_chunk(chunk)
      # Parse OpenAI streaming response format
      return nil unless chunk

      if chunk.dig("choices", 0, "delta", "content")
        Provider::LlmConcept::ChatStreamChunk.new(
          type: "output_text",
          data: chunk.dig("choices", 0, "delta", "content")
        )
      elsif chunk.dig("choices", 0, "finish_reason")
        Provider::LlmConcept::ChatStreamChunk.new(
          type: "response",
          data: build_chat_response(chunk)
        )
      end
    end

    def extract_function_requests(message)
      tool_calls = message["tool_calls"] || []
      
      tool_calls.map do |tool_call|
        Provider::LlmConcept::ChatFunctionRequest.new(
          id: tool_call["id"],
          call_id: tool_call["id"],
          function_name: tool_call.dig("function", "name"),
          function_args: JSON.parse(tool_call.dig("function", "arguments") || "{}")
        )
      end
    rescue JSON::ParserError
      []
    end

    def build_categorization_prompt(transactions, user_categories)
      categories_json = user_categories.map do |cat|
        {
          id: cat[:id],
          name: cat[:name],
          classification: cat[:classification]
        }
      end.to_json

      transactions_json = transactions.map do |txn|
        {
          id: txn[:id],
          name: txn[:name],
          amount: txn[:amount]
        }
      end.to_json

      <<~PROMPT
        You are helping categorize financial transactions. Here are the available categories:

        #{categories_json}

        Please categorize these transactions:

        #{transactions_json}

        Respond with a JSON array where each object has:
        - transaction_id: the ID of the transaction
        - category_name: the name of the best matching category (or null if no good match)

        Only use categories from the provided list.
      PROMPT
    end

    def parse_categorization_response(response, transactions)
      content = response.dig("choices", 0, "message", "content")
      return [] unless content

      begin
        categorizations = JSON.parse(content)
        categorizations.map do |cat|
          Provider::LlmConcept::AutoCategorization.new(
            transaction_id: cat["transaction_id"],
            category_name: cat["category_name"]
          )
        end
      rescue JSON::ParserError
        []
      end
    end

    def build_merchant_detection_prompt(transactions, user_merchants)
      merchants_json = user_merchants.map { |m| { name: m[:name] } }.to_json
      transactions_json = transactions.map do |txn|
        {
          id: txn[:id],
          name: txn[:name]
        }
      end.to_json

      <<~PROMPT
        You are helping detect merchant information from transaction names. Here are known merchants:

        #{merchants_json}

        Please analyze these transactions and detect merchant information:

        #{transactions_json}

        For each transaction, respond with a JSON array where each object has:
        - transaction_id: the ID of the transaction
        - business_name: the detected business name (or null)
        - business_url: the business website URL (or null)

        Try to identify real business names and websites when possible.
      PROMPT
    end

    def parse_merchant_detection_response(response, transactions)
      content = response.dig("choices", 0, "message", "content")
      return [] unless content

      begin
        detections = JSON.parse(content)
        detections.map do |det|
          Provider::LlmConcept::AutoDetectedMerchant.new(
            transaction_id: det["transaction_id"],
            business_name: det["business_name"],
            business_url: det["business_url"]
          )
        end
      rescue JSON::ParserError
        []
      end
    end
end