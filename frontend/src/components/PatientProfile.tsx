import React from 'react';
import { 
  ArrowLeft, 
  Phone, 
  Mail, 
  AlertTriangle, 
  TrendingUp,
  Calendar,
  Edit,
  Trash2
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';

const PatientProfile: React.FC = () => {
  return (
    <div className="p-6 max-w-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-4 min-w-0">
          <Button variant="ghost" size="icon" className="shrink-0">
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <h1 className="text-2xl font-bold truncate">Patient Profile</h1>
        </div>
        <div className="flex items-center space-x-2 shrink-0">
          <Button variant="outline" className="text-primary whitespace-nowrap">
            ACL Assistant
          </Button>
          <Button variant="outline" size="icon">
            <Edit className="h-4 w-4" />
          </Button>
          <Button variant="outline" size="icon" className="text-medical-red">
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Patient Info Card */}
      <Card className="mb-6">
        <CardContent className="p-6">
          <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between mb-6 space-y-4 lg:space-y-0">
            <div className="flex items-center space-x-4 min-w-0">
              <Avatar className="h-16 w-16 shrink-0">
                <AvatarFallback className="text-lg bg-primary text-primary-foreground">JD</AvatarFallback>
              </Avatar>
              <div className="min-w-0 flex-1">
                <div className="flex flex-col sm:flex-row sm:items-center sm:space-x-2 space-y-1 sm:space-y-0">
                  <h2 className="text-xl font-semibold truncate">John Doe</h2>
                  <Badge variant="destructive" className="w-fit">High Risk</Badge>
                </div>
                <p className="text-muted-foreground">1985-05-15 (40 years)</p>
                <div className="flex flex-col sm:flex-row sm:items-center sm:space-x-4 mt-2 space-y-1 sm:space-y-0">
                  <div className="flex items-center space-x-1">
                    <Phone className="h-4 w-4 text-muted-foreground shrink-0" />
                    <span className="text-sm">(555) 123-4567</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <Mail className="h-4 w-4 text-muted-foreground shrink-0" />
                    <span className="text-sm truncate">john.doe@example.com</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Insurance Information */}
            <div>
              <h3 className="font-semibold mb-3">Insurance Information</h3>
              <div className="space-y-2">
                <div>
                  <span className="text-sm text-muted-foreground">Provider</span>
                  <p className="font-medium">Blue Cross</p>
                </div>
                <div>
                  <span className="text-sm text-muted-foreground">Policy Number</span>
                  <p className="font-medium">BC123456789</p>
                </div>
              </div>
            </div>

            {/* Emergency Contact */}
            <div>
              <h3 className="font-semibold mb-3">Emergency Contact</h3>
              <div className="space-y-2">
                <div>
                  <span className="text-sm text-muted-foreground">Name</span>
                  <p className="font-medium">Jane Doe</p>
                </div>
                <div>
                  <span className="text-sm text-muted-foreground">Relationship</span>
                  <p className="font-medium">Spouse</p>
                </div>
                <div>
                  <span className="text-sm text-muted-foreground">Contact Number</span>
                  <p className="font-medium">(555) 987-6543</p>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Tabs */}
      <Tabs defaultValue="overview" className="space-y-6">
        <div className="overflow-x-auto">
          <TabsList className="grid w-full grid-cols-6 min-w-fit">
            <TabsTrigger value="overview" className="whitespace-nowrap">Overview</TabsTrigger>
            <TabsTrigger value="appointments" className="whitespace-nowrap">Appointments</TabsTrigger>
            <TabsTrigger value="vitals" className="whitespace-nowrap">Vitals</TabsTrigger>
            <TabsTrigger value="medications" className="whitespace-nowrap">Medications</TabsTrigger>
            <TabsTrigger value="notes" className="whitespace-nowrap">Notes</TabsTrigger>
            <TabsTrigger value="history" className="whitespace-nowrap">History</TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="overview" className="space-y-6">
          {/* High Risk Alert */}
          <Card className="border-medical-red/20 bg-medical-red/5">
            <CardContent className="p-4">
              <div className="flex items-center space-x-2">
                <AlertTriangle className="h-5 w-5 text-medical-red" />
                <div>
                  <h3 className="font-semibold text-medical-red">High Sepsis Risk (82%)</h3>
                  <p className="text-sm text-muted-foreground">
                    Based on rising WBC, fever, and low BP. Suggests immediate attention.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* AI Diagnosis Suggestions */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <TrendingUp className="h-5 w-5" />
                  <span>AI Diagnosis Suggestions</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-4 bg-medical-blue-light rounded-lg">
                    <div>
                      <h4 className="font-semibold text-lg">87%</h4>
                      <p className="text-sm text-muted-foreground">Pneumonia</p>
                      <p className="text-xs text-muted-foreground">
                        Supported by: Crackles on auscultation and CXR findings.
                      </p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Recent Vital Signs */}
            <Card>
              <CardHeader>
                <CardTitle>Recent Vital Signs</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {[
                    { date: '2025-05-15', bp: '138/88' },
                    { date: '2025-04-15', bp: '142/92' },
                    { date: '2025-03-15', bp: '136/86' }
                  ].map((vital, index) => (
                    <div key={index} className="flex justify-between items-center py-2 border-b border-border last:border-0">
                      <span className="text-sm text-muted-foreground">{vital.date}</span>
                      <span className="font-medium">{vital.bp}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Upcoming Appointments */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Calendar className="h-5 w-5" />
                <span>Upcoming Appointments</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground">No upcoming appointments scheduled.</p>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="appointments">
          <Card>
            <CardContent className="p-6">
              <p className="text-muted-foreground">Appointments management interface would be here.</p>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="vitals">
          <Card>
            <CardContent className="p-6">
              <p className="text-muted-foreground">Vital signs tracking interface would be here.</p>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="medications">
          <Card>
            <CardContent className="p-6">
              <p className="text-muted-foreground">Medications management interface would be here.</p>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="notes">
          <Card>
            <CardContent className="p-6">
              <p className="text-muted-foreground">Clinical notes interface would be here.</p>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="history">
          <Card>
            <CardContent className="p-6">
              <p className="text-muted-foreground">Patient history interface would be here.</p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default PatientProfile;
