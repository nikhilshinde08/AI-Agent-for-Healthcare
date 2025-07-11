import React, { useState, useRef, useEffect } from 'react';
import { MessageCircle, Send, X, Minimize2, Database, Clock, CheckCircle, AlertCircle, Lightbulb, RotateCcw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface Message {
  id: string;
  text: string;
  isUser: boolean;
  timestamp: Date;
  sql_query?: string;
  result_count?: number;
  processing_time?: number;
  success?: boolean;
  table_data?: TableData;
}

interface ChatAssistantProps {
  apiEndpoint?: string;
}

interface TableData {
  headers: string[];
  data: Record<string, any>[];
  row_count: number;
}

interface ApiResponse {
  response: string;
  sql_generated?: string;
  data: any[];
  result_count: number;
  success: boolean;
  session_id?: string;
  query_understanding?: string;
  table_data?: TableData;
  metadata?: {
    processing_time?: number;
    agent_type?: string;
  };
}

const ChatAssistant: React.FC<ChatAssistantProps> = ({ 
  apiEndpoint = 'http://127.0.0.1:8002/chat' 
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      text: "Hello! I'm your Healthcare Database Assistant. I can help you query patient data, medical records, and healthcare information.\n\n**Quick Start**: Try one of the recommended questions below, or type your own question about patients, conditions, medications, or healthcare analytics.",
      isUser: false,
      timestamp: new Date(),
      success: true
    }
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(true);
  const [usedQuestions, setUsedQuestions] = useState<Set<string>>(new Set());
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // All available questions in a flat array
  const allQuestions = [
    "How many patients do we have?",
    "Show me patients over 65 years old",
    "Find patients with no recent visits",
    "List patients by age group",
    "Show patients with diabetes",
    "What are the most common diagnoses?",
    "Find patients with heart conditions",
    "Show patients with chronic conditions",
    "What medications are prescribed most often?",
    "Show patients on blood pressure medication",
    "Find recent prescription changes",
    "List patients with medication allergies",
    "Show recent emergency room visits",
    "What are our busiest appointment days?",
    "Find patients needing follow-up care",
    "Show vaccination status overview",
    "Today's appointments",
    "Patients admitted this week",
    "Recent lab results",
    "Outstanding referrals",
    "Show patients by gender distribution",
    "Find patients with upcoming appointments",
    "List recent admissions",
    "Show patients with multiple conditions",
    "Find expired prescriptions",
    "Show average patient age",
    "List top 10 prescribed medications",
    "Find patients without insurance",
    "Show monthly visit trends",
    "List critical patients",
    "Find patients by zip code",
    "Show lab test results summary",
    "Find overdue checkups",
    "Show provider workload",
    "List emergency contacts needed",
    "Find pediatric patients",
    "Show seasonal health trends",
    "List medication interactions",
    "Find patients needing referrals",
    "Show appointment no-shows"
  ];

  // Get 5 random unused questions
  const getRandomQuestions = (): string[] => {
    const availableQuestions = allQuestions.filter(q => !usedQuestions.has(q));
    
    // If we've used all questions, reset the used questions set
    if (availableQuestions.length < 5) {
      setUsedQuestions(new Set());
      return allQuestions.slice().sort(() => Math.random() - 0.5).slice(0, 5);
    }
    
    // Shuffle and take 5 questions
    return availableQuestions.sort(() => Math.random() - 0.5).slice(0, 5);
  };

  const [currentQuestions, setCurrentQuestions] = useState<string[]>(() => getRandomQuestions());

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = async (messageText?: string) => {
    const textToSend = messageText || inputMessage;
    if (!textToSend.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      text: textToSend,
      isUser: true,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);
    setShowSuggestions(false); // Hide suggestions while processing

    try {
      const requestBody: any = { 
        message: textToSend 
      };
      
      // Include session ID if available
      if (sessionId) {
        requestBody.session_id = sessionId;
      }

      const response = await fetch(apiEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody)
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data: ApiResponse = await response.json();
      
      // Update session ID if provided
      if (data.session_id && !sessionId) {
        setSessionId(data.session_id);
      }
      
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: data.response || 'I apologize, but I encountered an error processing your request.',
        isUser: false,
        timestamp: new Date(),
        sql_query: data.sql_generated,
        result_count: data.result_count,
        processing_time: data.metadata?.processing_time,
        success: data.success,
        table_data: data.table_data
      };

      setMessages(prev => [...prev, assistantMessage]);
      
      // Generate new questions after each response
      const newQuestions = getRandomQuestions();
      setCurrentQuestions(newQuestions);
    } catch (error) {
      console.error('Chat API error:', error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: 'I apologize, but I\'m currently experiencing technical difficulties. Please try again later.',
        isUser: false,
        timestamp: new Date(),
        success: false
      };
      setMessages(prev => [...prev, errorMessage]);
      
      // Generate new questions even after errors
      const newQuestions = getRandomQuestions();
      setCurrentQuestions(newQuestions);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleSuggestionClick = (question: string) => {
    // Mark this question as used
    setUsedQuestions(prev => new Set(prev).add(question));
    
    // Generate new questions for next time
    const newQuestions = getRandomQuestions();
    setCurrentQuestions(newQuestions);
    
    setInputMessage(question);
    sendMessage(question);
  };

  const handleNewConversation = async () => {
    try {
      // Call backend to reset session
      const resetResponse = await fetch(`${apiEndpoint.replace('/chat', '/reset_session')}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId
        })
      });

      if (resetResponse.ok) {
        const resetData = await resetResponse.json();
        console.log('Session reset:', resetData.message);
        
        // Update frontend state
        setMessages([{
          id: '1',
          text: "Hello! I'm your Healthcare Database Assistant. I can help you query patient data, medical records, and healthcare information.\n\n**Quick Start**: Try one of the recommended questions below, or type your own question about patients, conditions, medications, or healthcare analytics.",
          isUser: false,
          timestamp: new Date(),
          success: true
        }]);
        setSessionId(resetData.session_id || null);
        setUsedQuestions(new Set());
        setCurrentQuestions(getRandomQuestions());
      } else {
        console.error('Failed to reset session:', resetResponse.statusText);
        // Fallback to frontend-only reset
        setMessages([{
          id: '1',
          text: "Hello! I'm your Healthcare Database Assistant. I can help you query patient data, medical records, and healthcare information.\n\n**Quick Start**: Try one of the recommended questions below, or type your own question about patients, conditions, medications, or healthcare analytics.",
          isUser: false,
          timestamp: new Date(),
          success: true
        }]);
        setSessionId(null);
        setUsedQuestions(new Set());
        setCurrentQuestions(getRandomQuestions());
      }
    } catch (error) {
      console.error('Error resetting session:', error);
      // Fallback to frontend-only reset
      setMessages([{
        id: '1',
        text: "Hello! I'm your Healthcare Database Assistant. I can help you query patient data, medical records, and healthcare information.\n\n**Quick Start**: Try one of the recommended questions below, or type your own question about patients, conditions, medications, or healthcare analytics.",
        isUser: false,
        timestamp: new Date(),
        success: true
      }]);
      setSessionId(null);
      setUsedQuestions(new Set());
      setCurrentQuestions(getRandomQuestions());
    }
  };

  const formatProcessingTime = (time?: number) => {
    if (!time) return '';
    return time < 1 ? `${(time * 1000).toFixed(0)}ms` : `${time.toFixed(2)}s`;
  };

  const renderMessageText = (text: string, tableData?: TableData) => {
    // If we have table data, render a proper table
    if (tableData && tableData.headers.length > 0) {
      return (
        <div className="space-y-3">
          {/* Message text */}
          <div className="text-sm leading-relaxed mb-4">
            {text.split('**').map((chunk, ci) => 
              ci % 2 === 1 ? <strong key={ci} className="font-semibold text-slate-700">{chunk}</strong> : chunk
            )}
          </div>
          
          {/* Data table */}
          <div className="overflow-x-auto rounded-lg border border-slate-200 shadow-md bg-white">
            <table className="w-full text-sm">
              <thead className="bg-gradient-to-r from-slate-100 to-slate-50 border-b-2 border-slate-200">
                <tr>
                  {tableData.headers.map((header, index) => (
                    <th key={index} className="px-6 py-4 text-left font-semibold text-slate-700 tracking-wider uppercase text-xs whitespace-nowrap">
                      {header}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {tableData.data.slice(0, 20).map((row, rowIndex) => (
                  <tr key={rowIndex} className="hover:bg-slate-50 transition-colors duration-200">
                    {tableData.headers.map((header, cellIndex) => (
                      <td key={cellIndex} className="px-6 py-4 text-slate-600 whitespace-nowrap">
                        {String(row[header] ?? '-')}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            {tableData.data.length > 20 && (
              <div className="px-6 py-3 text-center text-xs text-slate-500 bg-slate-50 border-t border-slate-200">
                Displaying first 20 of {tableData.row_count} records
              </div>
            )}
          </div>
        </div>
      );
    }
    
    // Check if message contains numbered list (looks for various numbered patterns)
    if (text.match(/\d+\.\s+\*\*[^*]+\*\*/) || text.match(/\d+\.\s+[^.]+:/) || text.match(/\d+\.\s+[A-Z]/) || text.match(/\d+\.\s+\w/)) {
      // Split on numbered items but keep the numbers
      const parts = text.split(/(?=\d+\.\s)/);
      const intro = parts[0];
      const listItems = parts.slice(1);
      
      return (
        <div className="space-y-2">
          {intro && intro.trim() && (
            <div className="mb-3 text-xs text-muted-foreground">
              {intro.split('**').map((chunk, ci) => 
                ci % 2 === 1 ? <strong key={ci}>{chunk}</strong> : chunk
              )}
            </div>
          )}
          
          {listItems.length > 0 && (
            <div className="space-y-1.5">
              {listItems.map((item, index) => {
                const match = item.match(/^(\d+)\.\s(.+)/s);
                if (match) {
                  const [, number, content] = match;
                  
                  // Parse for medication lists (with prescriptions count)
                  const medicationMatch = content.match(/\*\*([^*]+)\*\*(.+)/);
                  if (medicationMatch) {
                    const [, medicationName, details] = medicationMatch;
                    const countMatch = details.match(/(\d+[,\d]*)\s*(times|prescriptions)/);
                    const count = countMatch ? countMatch[1] : '';
                    
                    return (
                      <div key={index} className="flex items-center space-x-2 p-2 rounded border border-muted/40 bg-muted/10 hover:bg-muted/20 transition-colors">
                        <div className="flex-shrink-0 w-5 h-5 rounded-full bg-primary/20 flex items-center justify-center">
                          <span className="text-xs font-medium text-primary">{number}</span>
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="font-medium text-xs leading-tight text-foreground">
                            {medicationName}
                          </div>
                          {count && (
                            <div className="text-xs text-muted-foreground mt-0.5">
                              {count} prescriptions
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  }
                  
                  // Parse for provider lists (with ID and encounters/metrics)
                  const providerMatch = content.match(/\*\*Provider ID:\*\*\s*([^-]+)\s*-\s*\*\*([^:]+):\*\*\s*(.+)/);
                  if (providerMatch) {
                    const [, providerId, metricType, metricValue] = providerMatch;
                    
                    return (
                      <div key={index} className="flex items-center space-x-2 p-2 rounded border border-muted/40 bg-muted/10 hover:bg-muted/20 transition-colors">
                        <div className="flex-shrink-0 w-5 h-5 rounded-full bg-blue-100 flex items-center justify-center">
                          <span className="text-xs font-medium text-blue-600">{number}</span>
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="font-medium text-xs leading-tight text-foreground">
                            Provider ID: {providerId.trim()}
                          </div>
                          <div className="text-xs text-muted-foreground mt-0.5">
                            {metricType}: {metricValue.trim()}
                          </div>
                        </div>
                      </div>
                    );
                  }
                  
                  // Parse for simple name lists (names without additional data)
                  const nameMatch = content.match(/^([A-Z][a-zA-Z0-9\s]+)\s*$/);
                  if (nameMatch) {
                    const [, name] = nameMatch;
                    
                    return (
                      <div key={index} className="flex items-center space-x-2 p-2 rounded border border-muted/40 bg-muted/10 hover:bg-muted/20 transition-colors">
                        <div className="flex-shrink-0 w-5 h-5 rounded-full bg-green-100 flex items-center justify-center">
                          <span className="text-xs font-medium text-green-600">{number}</span>
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="font-medium text-xs leading-tight text-foreground">
                            {name.trim()}
                          </div>
                        </div>
                      </div>
                    );
                  }
                  
                  // Parse for date/appointment lists
                  const dateMatch = content.match(/\*\*([^*]+)\*\*\s*with\s*(\d+)\s*(appointments|encounters)/);
                  if (dateMatch) {
                    const [, date, count, type] = dateMatch;
                    
                    return (
                      <div key={index} className="flex items-center space-x-2 p-2 rounded border border-muted/40 bg-muted/10 hover:bg-muted/20 transition-colors">
                        <div className="flex-shrink-0 w-5 h-5 rounded-full bg-purple-100 flex items-center justify-center">
                          <span className="text-xs font-medium text-purple-600">{number}</span>
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="font-medium text-xs leading-tight text-foreground">
                            {date.trim()}
                          </div>
                          <div className="text-xs text-muted-foreground mt-0.5">
                            {count} {type}
                          </div>
                        </div>
                      </div>
                    );
                  }
                  
                  // General fallback for any numbered list
                  return (
                    <div key={index} className="flex items-center space-x-2 p-2 rounded border border-muted/40 bg-muted/10">
                      <div className="flex-shrink-0 w-5 h-5 rounded-full bg-primary/20 flex items-center justify-center">
                        <span className="text-xs font-medium text-primary">{number}</span>
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-xs leading-tight">
                          {content.split('**').map((chunk, ci) => 
                            ci % 2 === 1 ? <strong key={ci}>{chunk}</strong> : chunk
                          )}
                        </div>
                      </div>
                    </div>
                  );
                }
                return null;
              })}
            </div>
          )}
        </div>
      );
    }
    
    // Check for bullet lists with dashes
    if (text.match(/- \*\*[^*]+\*\*/)) {
      const parts = text.split(/(?=- \*\*)/);
      const intro = parts[0];
      const listItems = parts.slice(1);
      
      return (
        <div className="space-y-2">
          {intro && intro.trim() && (
            <div className="mb-3 text-xs text-muted-foreground">
              {intro.split('**').map((chunk, ci) => 
                ci % 2 === 1 ? <strong key={ci}>{chunk}</strong> : chunk
              )}
            </div>
          )}
          
          {listItems.length > 0 && (
            <div className="space-y-1">
              {listItems.map((item, index) => {
                const match = item.match(/^- (.+)/s);
                if (match) {
                  const [, content] = match;
                  const categoryMatch = content.match(/\*\*([^*]+)\*\*(.+)/);
                  
                  if (categoryMatch) {
                    const [, category, details] = categoryMatch;
                    const countMatch = details.match(/(\d+)\s*patients/);
                    const count = countMatch ? countMatch[1] : '';
                    
                    return (
                      <div key={index} className="flex items-center space-x-2 p-1.5 rounded border border-muted/30 bg-muted/5">
                        <div className="flex-shrink-0 w-1.5 h-1.5 rounded-full bg-primary"></div>
                        <div className="flex-1 min-w-0">
                          <span className="font-medium text-xs">{category}</span>
                          {count && (
                            <span className="ml-2 text-xs text-muted-foreground">
                              ({count} patients)
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  }
                }
                return null;
              })}
            </div>
          )}
        </div>
      );
    }
    
    // Regular text with basic markdown
    return (
      <div className="whitespace-pre-wrap">
        {text.split('**').map((chunk, ci) => 
          ci % 2 === 1 ? <strong key={ci}>{chunk}</strong> : chunk
        )}
      </div>
    );
  };

  if (!isOpen) {
    return (
      <Button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 h-14 w-14 rounded-full shadow-lg hover:shadow-xl transition-all duration-300 z-50 animate-fade-in"
        size="icon"
      >
        <MessageCircle className="h-6 w-6" />
      </Button>
    );
  }

  return (
    <Card className={`fixed right-6 bg-background border shadow-xl z-50 transition-all duration-300 flex flex-col ${
      isMinimized 
        ? 'bottom-6 w-80 h-16' 
        : 'bottom-6 w-[500px] h-[700px]'
    }`}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b text-white rounded-t-lg shadow-sm" style={{backgroundColor: '#4285F4'}}>
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-white/10 rounded-lg">
            <MessageCircle className="h-5 w-5" />
          </div>
          <div>
            <h2 className="font-semibold text-lg">Healthcare Database Assistant</h2>
            <p className="text-xs text-white/70">AI-Powered Data Analysis</p>
          </div>
          {sessionId && (
            <Badge variant="outline" className="text-xs border-white/30 text-white/90">
              Session: {sessionId.slice(-6)}
            </Badge>
          )}
        </div>
        <div className="flex items-center space-x-1">
          <Button
            variant="ghost"
            size="icon"
            onClick={handleNewConversation}
            className="h-8 w-8 text-white/80 hover:bg-white/10 hover:text-white transition-colors"
            title="New conversation"
          >
            <RotateCcw className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setShowDetails(!showDetails)}
            className="h-8 w-8 text-white/80 hover:bg-white/10 hover:text-white transition-colors"
            title="Toggle details"
          >
            <Database className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setIsMinimized(!isMinimized)}
            className="h-8 w-8 text-white/80 hover:bg-white/10 hover:text-white transition-colors"
          >
            <Minimize2 className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setIsOpen(false)}
            className="h-8 w-8 text-white/80 hover:bg-white/10 hover:text-white transition-colors"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {!isMinimized && (
        <>
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6 min-h-0 bg-gradient-to-b from-slate-50/30 to-white">
            {/* Show initial questions only for the first message */}
            {messages.length === 1 && (
              <div className="space-y-3 border-b pb-4 mb-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2 text-sm text-muted-foreground">
                    <Lightbulb className="h-4 w-4" />
                    <span className="font-medium">Try These Questions</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        const newQuestions = getRandomQuestions();
                        setCurrentQuestions(newQuestions);
                      }}
                      className="h-6 px-2 text-xs hover:bg-muted"
                      title="Get new questions"
                    >
                      <RotateCcw className="h-3 w-3" />
                    </Button>
                  </div>
                </div>
                
                <div className="grid gap-2">
                  {currentQuestions.map((question, index) => (
                    <Button
                      key={`${question}-${index}`}
                      variant="outline"
                      size="sm"
                      onClick={() => handleSuggestionClick(question)}
                      className="justify-start text-left h-auto py-3 px-4 text-sm hover:bg-slate-100 hover:border-slate-300 transition-colors border-slate-200 text-slate-600"
                      disabled={isLoading}
                    >
                      <span className="whitespace-normal leading-relaxed">
                        {question}
                      </span>
                    </Button>
                  ))}
                </div>
                
                <div className="text-center">
                  <p className="text-xs text-muted-foreground/70">
                    Click any question above or type your own below
                  </p>
                </div>
              </div>
            )}

            {messages.map((message, messageIndex) => (
              <div key={message.id}>
                <div className="w-full">
                  <div className={`w-full ${message.isUser ? 'pl-8' : 'pr-8'}`}>
                    <div className="flex items-start justify-between mb-3">
                      <div className={`text-base flex-1 leading-relaxed ${message.isUser ? 'font-medium text-slate-700' : 'text-slate-600'}`}>
                        {message.isUser && <span className="text-sm font-semibold text-slate-500 mr-3 block mb-1">You</span>}
                        {!message.isUser && <span className="text-sm font-semibold text-slate-500 mr-3 block mb-1">Assistant</span>}
                        <div className="pl-1">{renderMessageText(message.text, message.table_data)}</div>
                      </div>
                      {!message.isUser && message.success !== undefined && (
                        <div className="ml-2 flex-shrink-0">
                          {message.success ? (
                            <CheckCircle className="h-4 w-4 text-green-500" />
                          ) : (
                            <AlertCircle className="h-4 w-4 text-red-500" />
                          )}
                        </div>
                      )}
                    </div>
                    
                    {/* Query Details */}
                    {!message.isUser && showDetails && (message.sql_query || message.result_count !== undefined || message.processing_time) && (
                      <div className="mt-4 p-4 bg-slate-50 border border-slate-200 rounded-lg text-sm space-y-2">
                        {message.sql_query && (
                          <div className="flex items-start space-x-2">
                            <Database className="h-4 w-4 text-slate-500 mt-0.5" />
                            <div>
                              <span className="text-slate-500 font-medium">SQL Query:</span>
                              <code className="block text-xs font-mono bg-slate-100 px-2 py-1 rounded mt-1 text-slate-700">
                                {message.sql_query.length > 80 
                                  ? `${message.sql_query.substring(0, 80)}...` 
                                  : message.sql_query}
                              </code>
                            </div>
                          </div>
                        )}
                        {(message.result_count !== undefined || message.processing_time) && (
                          <div className="flex items-center space-x-4 text-slate-500">
                            {message.result_count !== undefined && (
                              <div className="flex items-center space-x-1">
                                <span className="font-medium">Records:</span>
                                <span className="bg-slate-200 px-2 py-0.5 rounded text-xs font-semibold">{message.result_count}</span>
                              </div>
                            )}
                            {message.processing_time && (
                              <div className="flex items-center space-x-1">
                                <Clock className="h-3 w-3" />
                                <span className="text-xs">{formatProcessingTime(message.processing_time)}</span>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                    
                    <p className="text-xs opacity-70 mt-1">
                      {message.timestamp.toLocaleTimeString([], { 
                        hour: '2-digit', 
                        minute: '2-digit' 
                      })}
                    </p>
                  </div>
                </div>
                
                {/* Show suggestions after each assistant response (not user messages and not the first welcome message) */}
                {!message.isUser && messageIndex > 0 && messageIndex === messages.length - 1 && !isLoading && (
                  <div className="mt-4 mb-4">
                    <div className="space-y-3 bg-muted/30 rounded-lg p-3 border border-muted">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2 text-sm text-muted-foreground">
                          <Lightbulb className="h-4 w-4" />
                          <span className="font-medium">Try These Questions Next</span>
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            const newQuestions = getRandomQuestions();
                            setCurrentQuestions(newQuestions);
                          }}
                          className="h-6 px-2 text-xs hover:bg-muted"
                          title="Get new questions"
                        >
                          <RotateCcw className="h-3 w-3" />
                        </Button>
                      </div>
                      
                      <div className="grid gap-2">
                        {currentQuestions.map((question, index) => (
                          <Button
                            key={`${question}-${index}-${messageIndex}`}
                            variant="outline"
                            size="sm"
                            onClick={() => handleSuggestionClick(question)}
                            className="justify-start text-left h-auto py-3 px-4 text-sm hover:bg-slate-100 hover:border-slate-300 transition-colors border-slate-200 text-slate-600 bg-white"
                            disabled={isLoading}
                          >
                            <span className="whitespace-normal leading-relaxed">
                              {question}
                            </span>
                          </Button>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))}
            {isLoading && (
              <div className="w-full">
                <div className="flex space-x-1 py-2">
                  <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                  <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="flex-shrink-0 p-6 border-t border-slate-200 bg-gradient-to-r from-slate-50 to-white">
            <div className="flex items-center space-x-3">
              <Input
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyDown={handleKeyPress}
                placeholder="Ask about patients, medications, or healthcare analytics..."
                className="flex-1 h-12 border-slate-300 text-base placeholder:text-slate-400"
                style={{'--tw-ring-color': '#4285F4'} as any}
                onFocus={(e) => {
                  e.currentTarget.style.borderColor = '#4285F4';
                  e.currentTarget.style.boxShadow = '0 0 0 1px #4285F4';
                }}
                onBlur={(e) => {
                  e.currentTarget.style.borderColor = '#CBD5E1';
                  e.currentTarget.style.boxShadow = 'none';
                }}
                disabled={isLoading}
              />
              <Button 
                onClick={() => sendMessage()} 
                disabled={!inputMessage.trim() || isLoading}
                size="icon"
                className="h-12 w-12 flex-shrink-0 transition-colors text-white"
                style={{backgroundColor: '#4285F4'}}
                onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#3367D6'}
                onMouseLeave={(e) => e.currentTarget.style.backgroundColor = '#4285F4'}
              >
                <Send className="h-5 w-5" />
              </Button>
            </div>
            <div className="flex items-center justify-between mt-2 text-xs text-muted-foreground">
              <span className="truncate">Ask questions about healthcare data or use the suggestions above</span>
              {sessionId && (
                <span className="ml-2 flex-shrink-0">Session: {sessionId.slice(-8)}</span>
              )}
            </div>
          </div>
        </>
      )}
    </Card>
  );
};

export default ChatAssistant;