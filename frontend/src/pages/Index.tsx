import React, { useState } from 'react';
import Sidebar from '@/components/Sidebar';
import Header from '@/components/Header';
import PatientProfile from '@/components/PatientProfile';
import ChatAssistant from '@/components/ChatAssistant';
import Analytics from '@/components/Analytics';

const Index = () => {
  const [activeTab, setActiveTab] = useState('patients');

  const renderMainContent = () => {
    switch (activeTab) {
      case 'analytics':
        return <Analytics apiBaseUrl="http://127.0.0.1:8002" />;
      case 'patients':
      default:
        return <PatientProfile />;
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="flex h-screen">
        {/* Sidebar */}
        <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />
        
        {/* Main Content Area */}
        <div className="flex-1 flex flex-col min-w-0">
          <Header />
          <main className="flex-1 overflow-auto p-6">
            {renderMainContent()}
          </main>
        </div>
      </div>

      {/* Chat Assistant - Dynamic Component */}
      <ChatAssistant apiEndpoint="http://127.0.0.1:8002/chat" />
    </div>
  );
};

export default Index;
