//+------------------------------------------------------------------+
//|                                                  AI_Trading_EA.mq4 |
//|                                    ZeroMQ Bridge for AI Agents    |
//+------------------------------------------------------------------+
#property copyright "AI Trading System"
#property version   "1.0"
#property strict

// Include ZeroMQ library (download from: https://github.com/dingmaotu/mql-zmq)
#include <Zmq/Zmq.mqh>

// Configuration
input int ZmqPort = 5555;           // Port for receiving commands
input bool VerboseLogging = true;   // Enable logging

// ZeroMQ socket
Context context;
Socket socket;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    Print("🤖 AI Trading EA Initializing...");
    
    // Initialize ZeroMQ socket
    context.init();
    socket.init(context, ZMQ_REP);
    
    // Bind to port
    if (!socket.bind(StringFormat("tcp://*:%d", ZmqPort)))
    {
        Print("❌ Failed to bind to port ", ZmqPort);
        return INIT_FAILED;
    }
    
    Print("✅ ZeroMQ bridge active on port ", ZmqPort);
    Print("📡 Waiting for AI agent commands...");
    
    return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    Print("🤖 AI Trading EA shutting down...");
    socket.close();
    context.destroy();
    Print("✅ Shutdown complete");
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
    // Check for incoming messages
    ZmqMsg request;
    
    if (socket.recv(request, ZMQ_DONTWAIT))
    {
        // Process the request
        string requestStr = request.getData();
        string response = ProcessCommand(requestStr);
        
        // Send response
        ZmqMsg reply;
        reply.setData(response);
        socket.send(reply);
    }
}

//+------------------------------------------------------------------+
//| Process incoming commands                                        |
//+------------------------------------------------------------------+
string ProcessCommand(string requestStr)
{
    if (VerboseLogging) Print("📨 Received: ", requestStr);
    
    // Parse JSON
    // Note: In production, use a JSON library
    // For simplicity, using string parsing
    
    string response = "";
    
    if (StringFind(requestStr, "PING") >= 0)
    {
        response = '{"status":"OK","message":"MT4 is online"}';
    }
    else if (StringFind(requestStr, "PRICE") >= 0)
    {
        string symbol = ExtractSymbol(requestStr);
        response = GetPrice(symbol);
    }
    else if (StringFind(requestStr, "BUY") >= 0)
    {
        response = ExecuteBuy(requestStr);
    }
    else if (StringFind(requestStr, "SELL") >= 0)
    {
        response = ExecuteSell(requestStr);
    }
    else if (StringFind(requestStr, "CLOSE") >= 0)
    {
        int ticket = ExtractTicket(requestStr);
        response = ClosePosition(ticket);
    }
    else if (StringFind(requestStr, "POSITIONS") >= 0)
    {
        response = GetPositions();
    }
    else if (StringFind(requestStr, "ACCOUNT") >= 0)
    {
        response = GetAccountInfo();
    }
    else
    {
        response = '{"error":"Unknown command"}';
    }
    
    if (VerboseLogging) Print("📤 Response: ", response);
    
    return response;
}

//+------------------------------------------------------------------+
//| Get current price for symbol                                     |
//+------------------------------------------------------------------+
string GetPrice(string symbol)
{
    double bid = MarketInfo(symbol, MODE_BID);
    double ask = MarketInfo(symbol, MODE_ASK);
    double spread = (ask - bid) / Point;
    
    return StringFormat(
        '{"symbol":"%s","bid":%.5f,"ask":%.5f,"spread":%.1f,"success":true}',
        symbol, bid, ask, spread
    );
}

//+------------------------------------------------------------------+
//| Execute market BUY order                                         |
//+------------------------------------------------------------------+
string ExecuteBuy(string requestStr)
{
    string symbol = ExtractSymbol(requestStr);
    double volume = ExtractVolume(requestStr);
    double stopLoss = ExtractStopLoss(requestStr);
    double takeProfit = ExtractTakeProfit(requestStr);
    string comment = ExtractComment(requestStr);
    
    // Refresh rates
    RefreshRates();
    
    double ask = MarketInfo(symbol, MODE_ASK);
    int slippage = 10; // pips
    
    int ticket = OrderSend(
        symbol,           // symbol
        OP_BUY,          // operation
        volume,          // volume
        ask,             // price
        slippage,        // slippage
        stopLoss,        // stop loss
        takeProfit,      // take profit
        comment,         // comment
        0,               // magic number
        0,               // expiration
        clrGreen         // arrow color
    );
    
    if (ticket > 0)
    {
        Print("✅ BUY order executed: ", ticket, " at ", ask);
        return StringFormat(
            '{"success":true,"ticket":%d,"price":%.5f,"symbol":"%s","volume":%.2f}',
            ticket, ask, symbol, volume
        );
    }
    else
    {
        int error = GetLastError();
        Print("❌ BUY failed. Error: ", error);
        return StringFormat(
            '{"success":false,"error":"OrderSend failed. Error %d","symbol":"%s"}',
            error, symbol
        );
    }
}

//+------------------------------------------------------------------+
//| Execute market SELL order                                        |
//+------------------------------------------------------------------+
string ExecuteSell(string requestStr)
{
    string symbol = ExtractSymbol(requestStr);
    double volume = ExtractVolume(requestStr);
    double stopLoss = ExtractStopLoss(requestStr);
    double takeProfit = ExtractTakeProfit(requestStr);
    string comment = ExtractComment(requestStr);
    
    // Refresh rates
    RefreshRates();
    
    double bid = MarketInfo(symbol, MODE_BID);
    int slippage = 10;
    
    int ticket = OrderSend(
        symbol,           // symbol
        OP_SELL,         // operation
        volume,          // volume
        bid,             // price
        slippage,        // slippage
        stopLoss,        // stop loss
        takeProfit,      // take profit
        comment,         // comment
        0,               // magic number
        0,               // expiration
        clrRed           // arrow color
    );
    
    if (ticket > 0)
    {
        Print("✅ SELL order executed: ", ticket, " at ", bid);
        return StringFormat(
            '{"success":true,"ticket":%d,"price":%.5f,"symbol":"%s","volume":%.2f}',
            ticket, bid, symbol, volume
        );
    }
    else
    {
        int error = GetLastError();
        Print("❌ SELL failed. Error: ", error);
        return StringFormat(
            '{"success":false,"error":"OrderSend failed. Error %d","symbol":"%s"}',
            error, symbol
        );
    }
}

//+------------------------------------------------------------------+
//| Close position by ticket                                         |
//+------------------------------------------------------------------+
string ClosePosition(int ticket)
{
    if (!OrderSelect(ticket, SELECT_BY_TICKET))
    {
        return StringFormat('{"success":false,"error":"Order %d not found"}', ticket);
    }
    
    double closePrice;
    if (OrderType() == OP_BUY)
        closePrice = MarketInfo(OrderSymbol(), MODE_BID);
    else
        closePrice = MarketInfo(OrderSymbol(), MODE_ASK);
    
    if (OrderClose(ticket, OrderLots(), closePrice, 10, clrWhite))
    {
        Print("✅ Position closed: ", ticket);
        return StringFormat('{"success":true,"ticket":%d,"closePrice":%.5f}', ticket, closePrice);
    }
    else
    {
        int error = GetLastError();
        return StringFormat('{"success":false,"error":"Close failed. Error %d"}', error);
    }
}

//+------------------------------------------------------------------+
//| Get all open positions                                           |
//+------------------------------------------------------------------+
string GetPositions()
{
    string result = "{\"positions\":[";
    int count = 0;
    
    for (int i = 0; i < OrdersTotal(); i++)
    {
        if (OrderSelect(i, SELECT_BY_POS))
        {
            if (count > 0) result += ",";
            result += StringFormat(
                '{"ticket":%d,"symbol":"%s","type":"%s","volume":%.2f,"openPrice":%.5f,"currentPrice":%.5f,"profit":%.2f,"stopLoss":%.5f,"takeProfit":%.5f}',
                OrderTicket(),
                OrderSymbol(),
                OrderType() == OP_BUY ? "BUY" : "SELL",
                OrderLots(),
                OrderOpenPrice(),
                OrderType() == OP_BUY ? MarketInfo(OrderSymbol(), MODE_BID) : MarketInfo(OrderSymbol(), MODE_ASK),
                OrderProfit(),
                OrderStopLoss(),
                OrderTakeProfit()
            );
            count++;
        }
    }
    
    result += "]}";
    return result;
}

//+------------------------------------------------------------------+
//| Get account information                                          |
//+------------------------------------------------------------------+
string GetAccountInfo()
{
    return StringFormat(
        '{"balance":%.2f,"equity":%.2f,"margin":%.2f,"freeMargin":%.2f,"leverage":%d,"currency":"%s","server":"%s"}',
        AccountBalance(),
        AccountEquity(),
        AccountMargin(),
        AccountFreeMargin(),
        AccountLeverage(),
        AccountCurrency(),
        AccountServer()
    );
}

//+------------------------------------------------------------------+
//| Helper functions (simplified JSON parsing)                       |
//+------------------------------------------------------------------+
string ExtractSymbol(string json)
{
    int pos = StringFind(json, "symbol");
    if (pos < 0) return "EURUSD";
    
    int start = StringFind(json, ":", pos) + 3;
    int end = StringFind(json, "\"", start);
    return StringSubstr(json, start, end - start);
}

double ExtractVolume(string json)
{
    int pos = StringFind(json, "volume");
    if (pos < 0) return 0.01;
    
    int start = StringFind(json, ":", pos) + 1;
    int end = StringFind(json, ",", start);
    if (end < 0) end = StringFind(json, "}", start);
    
    return StrToDouble(StringSubstr(json, start, end - start));
}

double ExtractStopLoss(string json)
{
    int pos = StringFind(json, "stop_loss");
    if (pos < 0) return 0;
    
    int start = StringFind(json, ":", pos) + 1;
    int end = StringFind(json, ",", start);
    if (end < 0) end = StringFind(json, "}", start);
    
    return StrToDouble(StringSubstr(json, start, end - start));
}

double ExtractTakeProfit(string json)
{
    int pos = StringFind(json, "take_profit");
    if (pos < 0) return 0;
    
    int start = StringFind(json, ":", pos) + 1;
    int end = StringFind(json, ",", start);
    if (end < 0) end = StringFind(json, "}", start);
    
    return StrToDouble(StringSubstr(json, start, end - start));
}

string ExtractComment(string json)
{
    int pos = StringFind(json, "comment");
    if (pos < 0) return "AI_Trade";
    
    int start = StringFind(json, ":", pos) + 3;
    int end = StringFind(json, "\"", start);
    return StringSubstr(json, start, end - start);
}

int ExtractTicket(string json)
{
    int pos = StringFind(json, "ticket");
    if (pos < 0) return 0;
    
    int start = StringFind(json, ":", pos) + 1;
    int end = StringFind(json, ",", start);
    if (end < 0) end = StringFind(json, "}", start);
    
    return StrToInteger(StringSubstr(json, start, end - start));
}
//+------------------------------------------------------------------+
