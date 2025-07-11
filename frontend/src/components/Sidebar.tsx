import React from 'react';
import { 
  LayoutDashboard, 
  Users, 
  Calendar, 
  FileText, 
  Activity, 
  Pill, 
  BarChart3,
  Settings, 
  HelpCircle 
} from 'lucide-react';
import { Button } from '@/components/ui/button';

const sidebarItems = [
  { icon: LayoutDashboard, label: 'Dashboard', isActive: false, id: 'dashboard' },
  { icon: Users, label: 'Patients', isActive: true, id: 'patients' },
  { icon: Calendar, label: 'Appointments', isActive: false, id: 'appointments' },
  { icon: FileText, label: 'Medical Records', isActive: false, id: 'records' },
  { icon: Activity, label: 'Vitals', isActive: false, id: 'vitals' },
  { icon: Pill, label: 'Medications', isActive: false, id: 'medications' },
  { icon: BarChart3, label: 'Analytics', isActive: false, id: 'analytics' },
];

const bottomItems = [
  { icon: Settings, label: 'Settings' },
  { icon: HelpCircle, label: 'Help' },
];

interface SidebarProps {
  activeTab?: string;
  onTabChange?: (tabId: string) => void;
}

const Sidebar: React.FC<SidebarProps> = ({ activeTab = 'patients', onTabChange }) => {
  return (
    <div className="w-64 bg-card border-r border-border flex flex-col shrink-0">
      {/* Logo */}
      <div className="p-6 border-b border-border shrink-0">
        <div className="flex items-center space-x-2">
          <div className="w-8 h-8 bg-primary rounded flex items-center justify-center">
            <span className="text-primary-foreground font-bold text-sm">ACL</span>
          </div>
          <span className="font-semibold text-lg">Digital</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4">
        <div className="space-y-1">
          {sidebarItems.map((item, index) => {
            const Icon = item.icon;
            return (
              <Button
                key={index}
                variant={activeTab === item.id ? "default" : "ghost"}
                className={`w-full justify-start ${
                  activeTab === item.id ? '' : 'text-muted-foreground hover:text-foreground'
                }`}
                onClick={() => onTabChange?.(item.id)}
              >
                <Icon className="mr-3 h-4 w-4" />
                {item.label}
              </Button>
            );
          })}
        </div>
      </nav>

      {/* Bottom items */}
      <div className="p-4 border-t border-border">
        <div className="space-y-1">
          {bottomItems.map((item, index) => {
            const Icon = item.icon;
            return (
              <Button
                key={index}
                variant="ghost"
                className="w-full justify-start text-muted-foreground hover:text-foreground"
              >
                <Icon className="mr-3 h-4 w-4" />
                {item.label}
              </Button>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default Sidebar;