//+------------------------------------------------------------------+
void OnTick() {
    string filename = "AI_Commands.txt";
    int handle = FileOpen(filename, FILE_READ|FILE_TXT);
    
    if(handle != INVALID_HANDLE) {
        string command_text = FileReadString(handle);
        FileClose(handle);
        
        // Parse command
        if(StringFind(command_text, "PRICE") >= 0) {
            // Extract symbol (simple parsing)
            string symbol = "GOLD"; // Default
            if(StringFind(command_text, "\"symbol\":") >= 0) {
                // Parse JSON (simplified - use proper JSON parser for production)
                int start = StringFind(command_text, "\"symbol\":\"") + 10;
                int end = StringFind(command_text, "\"", start);
                symbol = StringSubstr(command_text, start, end - start);
            }
            
            // Get price
            double bid = MarketInfo(symbol, MODE_BID);
            double ask = MarketInfo(symbol, MODE_ASK);
            double spread = (ask - bid) / Point;
            
            // Write response
            string response = StringFormat(
                "{\"success\":true,\"symbol\":\"%s\",\"bid\":%.5f,\"ask\":%.5f,\"spread\":%.1f}",
                symbol, bid, ask, spread
            );
            
            FileDelete("AI_Responses.txt");
            int resp_handle = FileOpen("AI_Responses.txt", FILE_WRITE|FILE_TXT);
            if(resp_handle != INVALID_HANDLE) {
                FileWrite(resp_handle, response);
                FileClose(resp_handle);
            }
        }
        else if(StringFind(command_text, "PING") >= 0) {
            FileDelete("AI_Responses.txt");
            int resp_handle = FileOpen("AI_Responses.txt", FILE_WRITE|FILE_TXT);
            if(resp_handle != INVALID_HANDLE) {
                FileWrite(resp_handle, "{\"status\":\"OK\"}");
                FileClose(resp_handle);
            }
        }
        
        FileDelete(filename);
    }
}
//+------------------------------------------------------------------+