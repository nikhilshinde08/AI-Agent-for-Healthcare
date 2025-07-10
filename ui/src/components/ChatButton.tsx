import { useState } from 'react';
import { MessageCircle, X, Send, Settings } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'assistant';
  timestamp: Date;
}

interface ChatButtonProps {
  apiEndpoint?: string;
}

export const ChatButton = ({ apiEndpoint: initialEndpoint }: ChatButtonProps) => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      text: 'Hello! I\'m your healthcare database assistant. I can help you query your medical data and answer questions about patients, conditions, medications, and more. What would you like to know?',
      sender: 'assistant',
      timestamp: new Date()
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [apiEndpoint, setApiEndpoint] = useState(initialEndpoint || 'http://localhost:8002/chat');
  const [showSettings, setShowSettings] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string>(
    `web_${Date.now().toString()}`
  );

  const handleSendMessage = async () => {
    if (!inputValue.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      text: inputValue,
      sender: 'user',
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      if (apiEndpoint) {
        const response = await fetch(apiEndpoint, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            message: inputValue,
            session_id: sessionId,
            timestamp: new Date().toISOString()
          })
        });

        if (response.ok) {
          const data = await response.json();
          let responseText = data.response || data.message || 'I received your message.';
          
          // Format response more concisely
          if (data.sql_generated) {
            responseText += `\n\n**SQL:**\n\`\`\`sql\n${data.sql_generated}\n\`\`\``;
          }
          
          if (data.data && data.result_count) {
            responseText += `\n\n**Results:** ${data.result_count} record${data.result_count !== 1 ? 's' : ''} found`;
          }
          
          const assistantMessage: Message = {
            id: (Date.now() + 1).toString(),
            text: responseText,
            sender: 'assistant',
            timestamp: new Date()
          };
          setMessages(prev => [...prev, assistantMessage]);
        } else {
          throw new Error(`API request failed: ${response.status}`);
        }
      } else {
        // Fallback response when no API endpoint is configured
        setTimeout(() => {
          const assistantMessage: Message = {
            id: (Date.now() + 1).toString(),
            text: 'Thank you for your message. Please configure an API endpoint to enable full functionality.',
            sender: 'assistant',
            timestamp: new Date()
          };
          setMessages(prev => [...prev, assistantMessage]);
        }, 1000);
      }
    } catch (error) {
      console.error('Chat error:', error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: 'I apologize, but I\'m having trouble connecting to the database. Please check if the API server is running and try again.',
        sender: 'assistant',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const toggleChat = () => {
    setIsOpen(!isOpen);
    if (showSettings) setShowSettings(false);
  };

  return (
    <div className="fixed bottom-6 right-6 z-50">
      {/* Chat Window */}
      {isOpen && (
        <Card className="w-80 h-96 mb-4 shadow-lg border-0 bg-gradient-to-br from-card to-secondary/30 backdrop-blur-sm">
          <CardHeader className="pb-3 bg-gradient-to-r from-primary to-accent text-white rounded-t-lg">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <div className="w-2 h-2 bg-accent rounded-full animate-pulse"></div>
                Healthcare Database Assistant
              </CardTitle>
              <div className="flex items-center gap-1">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowSettings(!showSettings)}
                  className="h-6 w-6 p-0 hover:bg-white/20"
                >
                  <Settings className="h-3 w-3" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={toggleChat}
                  className="h-6 w-6 p-0 hover:bg-white/20"
                >
                  <X className="h-3 w-3" />
                </Button>
              </div>
            </div>
          </CardHeader>

          <CardContent className="p-0 flex flex-col h-full">
            {/* Settings Panel */}
            {showSettings && (
              <div className="p-3 border-b bg-muted/50">
                <div className="space-y-2">
                  <label className="text-xs font-medium text-muted-foreground">API Endpoint</label>
                  <Input
                    value={apiEndpoint}
                    onChange={(e) => setApiEndpoint(e.target.value)}
                    placeholder="http://localhost:8002/chat"
                    className="h-8 text-xs"
                  />
                  <div className="flex items-center gap-2">
                    <Badge variant={apiEndpoint ? "default" : "secondary"} className="text-xs">
                      {apiEndpoint ? "Connected" : "Not Connected"}
                    </Badge>
                  </div>
                </div>
              </div>
            )}

            {/* Messages */}
            <ScrollArea className="flex-1 p-3">
              <div className="space-y-3">
                {messages.map((message) => (
                  <div
                    key={message.id}
                    className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[80%] rounded-lg p-3 text-sm whitespace-pre-wrap ${
                        message.sender === 'user'
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-secondary text-secondary-foreground'
                      }`}
                    >
                      <div className="prose prose-sm max-w-none">
                        {message.text.split('\n').map((line, i) => {
                          if (line.startsWith('```sql')) {
                            return <div key={i} className="font-mono text-xs bg-gray-100 p-2 rounded mt-1">{line.slice(6)}</div>;
                          }
                          if (line === '```') {
                            return <div key={i}></div>;
                          }
                          if (line.startsWith('**') && line.endsWith('**')) {
                            return <div key={i} className="font-semibold text-xs mt-2 mb-1">{line.slice(2, -2)}</div>;
                          }
                          return <div key={i}>{line}</div>;
                        })}
                      </div>
                    </div>
                  </div>
                ))}
                {isLoading && (
                  <div className="flex justify-start">
                    <div className="bg-secondary text-secondary-foreground rounded-lg p-2 text-sm">
                      <div className="flex items-center gap-1">
                        <div className="w-2 h-2 bg-medical-blue rounded-full animate-pulse"></div>
                        <div className="w-2 h-2 bg-medical-blue rounded-full animate-pulse" style={{ animationDelay: '0.2s' }}></div>
                        <div className="w-2 h-2 bg-medical-blue rounded-full animate-pulse" style={{ animationDelay: '0.4s' }}></div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </ScrollArea>

            {/* Input */}
            <div className="p-3 border-t bg-background/50">
              <div className="flex gap-2">
                <Input
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Ask about your healthcare data..."
                  className="flex-1 h-8 text-sm"
                  disabled={isLoading}
                />
                <Button
                  onClick={handleSendMessage}
                  disabled={!inputValue.trim() || isLoading}
                  size="sm"
                  className="h-8 w-8 p-0"
                >
                  <Send className="h-3 w-3" />
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Chat Button */}
      <Button
        onClick={toggleChat}
        className="h-12 w-12 rounded-full shadow-lg bg-gradient-to-r from-primary to-accent hover:from-primary-glow hover:to-accent border-0 transition-all duration-300 hover:scale-110"
        size="sm"
      >
        {isOpen ? (
          <X className="h-5 w-5" />
        ) : (
          <MessageCircle className="h-5 w-5" />
        )}
      </Button>
    </div>
  );
};