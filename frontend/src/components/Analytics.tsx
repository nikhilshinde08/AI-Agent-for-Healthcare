import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line } from 'recharts';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { AlertCircle, CheckCircle, Database, Clock, Users, Activity, HardDrive, RefreshCw } from 'lucide-react';

interface AnalyticsData {
  period: {
    start_date: string;
    end_date: string;
    days: number;
  };
  daily_stats: Array<{
    date: string;
    total_requests: number;
    successful_requests: number;
    failed_requests: number;
    unique_sessions: number;
    avg_response_time: number;
  }>;
  hourly_stats: Array<{
    hour: number;
    total_requests: number;
    successful_requests: number;
    failed_requests: number;
  }>;
  top_endpoints: Array<{
    endpoint: string;
    request_count: number;
  }>;
  session_stats: {
    total_sessions: number;
    active_sessions: number;
    avg_requests_per_session: number;
    avg_session_response_time: number;
  };
}

interface StorageStats {
  database_stats: {
    total_requests: number;
    total_responses: number;
    total_sessions: number;
    active_sessions: number;
    db_size_mb: number;
  };
  total_storage: {
    size_mb: number;
    size_gb: number;
  };
  file_stats: {
    [key: string]: {
      file_count: number;
      size_mb: number;
    };
  };
}

interface AnalyticsProps {
  apiBaseUrl?: string;
}

const Analytics: React.FC<AnalyticsProps> = ({ 
  apiBaseUrl = 'http://127.0.0.1:8002' 
}) => {
  const [analyticsData, setAnalyticsData] = useState<AnalyticsData | null>(null);
  const [storageStats, setStorageStats] = useState<StorageStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [days, setDays] = useState(7);

  const fetchAnalytics = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const [analyticsResponse, storageResponse] = await Promise.all([
        fetch(`${apiBaseUrl}/analytics?days=${days}`),
        fetch(`${apiBaseUrl}/storage/stats`)
      ]);

      if (!analyticsResponse.ok || !storageResponse.ok) {
        throw new Error('Failed to fetch data');
      }

      const analytics = await analyticsResponse.json();
      const storage = await storageResponse.json();
      
      setAnalyticsData(analytics);
      setStorageStats(storage);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch analytics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, [days]);

  const formatHour = (hour: number) => {
    return `${hour.toString().padStart(2, '0')}:00`;
  };

  const calculateSuccessRate = (successful: number, total: number) => {
    if (total === 0) return 0;
    return ((successful / total) * 100).toFixed(1);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <RefreshCw className="h-6 w-6 animate-spin mr-2" />
        <span>Loading analytics...</span>
      </div>
    );
  }

  if (error) {
    return (
      <Card className="p-6">
        <div className="flex items-center space-x-2 text-red-600">
          <AlertCircle className="h-5 w-5" />
          <span>Error loading analytics: {error}</span>
        </div>
        <Button onClick={fetchAnalytics} className="mt-4">
          Retry
        </Button>
      </Card>
    );
  }

  if (!analyticsData || !storageStats) {
    return (
      <div className="text-center p-8">
        <span>No analytics data available</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">API Analytics</h2>
          <p className="text-muted-foreground">
            Analytics for {analyticsData.period.start_date} to {analyticsData.period.end_date}
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Button
            variant={days === 1 ? "default" : "outline"}
            size="sm"
            onClick={() => setDays(1)}
          >
            1D
          </Button>
          <Button
            variant={days === 7 ? "default" : "outline"}
            size="sm"
            onClick={() => setDays(7)}
          >
            7D
          </Button>
          <Button
            variant={days === 30 ? "default" : "outline"}
            size="sm"
            onClick={() => setDays(30)}
          >
            30D
          </Button>
          <Button onClick={fetchAnalytics} size="sm" variant="outline">
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Requests</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {analyticsData.daily_stats.reduce((sum, day) => sum + day.total_requests, 0)}
            </div>
            <p className="text-xs text-muted-foreground">
              Success rate: {calculateSuccessRate(
                analyticsData.daily_stats.reduce((sum, day) => sum + day.successful_requests, 0),
                analyticsData.daily_stats.reduce((sum, day) => sum + day.total_requests, 0)
              )}%
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Sessions</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {analyticsData.session_stats.active_sessions}
            </div>
            <p className="text-xs text-muted-foreground">
              Total: {analyticsData.session_stats.total_sessions}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Response Time</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {analyticsData.session_stats.avg_session_response_time?.toFixed(2) || 0}s
            </div>
            <p className="text-xs text-muted-foreground">
              Per session average
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Storage Used</CardTitle>
            <HardDrive className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {storageStats.total_storage.size_mb.toFixed(1)} MB
            </div>
            <p className="text-xs text-muted-foreground">
              Database: {storageStats.database_stats.db_size_mb.toFixed(1)} MB
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      <Tabs defaultValue="daily" className="space-y-4">
        <TabsList>
          <TabsTrigger value="daily">Daily Overview</TabsTrigger>
          <TabsTrigger value="hourly">Hourly Distribution</TabsTrigger>
          <TabsTrigger value="storage">Storage Details</TabsTrigger>
        </TabsList>

        <TabsContent value="daily" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Daily Request Volume</CardTitle>
              <CardDescription>
                Total requests and success rate over time
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={analyticsData.daily_stats}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="successful_requests" fill="#22c55e" name="Successful" />
                  <Bar dataKey="failed_requests" fill="#ef4444" name="Failed" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Response Time Trend</CardTitle>
              <CardDescription>
                Average response time per day
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={analyticsData.daily_stats}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Line 
                    type="monotone" 
                    dataKey="avg_response_time" 
                    stroke="#3b82f6" 
                    name="Response Time (s)"
                  />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="hourly" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Hourly Request Distribution</CardTitle>
              <CardDescription>
                Request volume by hour of day
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={analyticsData.hourly_stats}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="hour" tickFormatter={formatHour} />
                  <YAxis />
                  <Tooltip labelFormatter={(hour) => `Hour: ${formatHour(hour as number)}`} />
                  <Bar dataKey="total_requests" fill="#3b82f6" name="Total Requests" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle>Top Endpoints</CardTitle>
                <CardDescription>Most frequently used API endpoints</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {analyticsData.top_endpoints.map((endpoint, index) => (
                    <div key={endpoint.endpoint} className="flex items-center justify-between">
                      <span className="text-sm font-mono">{endpoint.endpoint}</span>
                      <Badge variant="secondary">{endpoint.request_count}</Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Session Statistics</CardTitle>
                <CardDescription>Session engagement metrics</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Active Sessions</span>
                    <div className="flex items-center space-x-2">
                      <CheckCircle className="h-4 w-4 text-green-500" />
                      <span className="font-semibold">{analyticsData.session_stats.active_sessions}</span>
                    </div>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Avg Requests/Session</span>
                    <span className="font-semibold">
                      {analyticsData.session_stats.avg_requests_per_session?.toFixed(1) || 0}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Avg Session Time</span>
                    <span className="font-semibold">
                      {analyticsData.session_stats.avg_session_response_time?.toFixed(2) || 0}s
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="storage" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle>Database Statistics</CardTitle>
                <CardDescription>Database usage and storage</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Total Requests</span>
                    <span className="font-semibold">{storageStats.database_stats.total_requests}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Total Responses</span>
                    <span className="font-semibold">{storageStats.database_stats.total_responses}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Total Sessions</span>
                    <span className="font-semibold">{storageStats.database_stats.total_sessions}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Database Size</span>
                    <span className="font-semibold">{storageStats.database_stats.db_size_mb.toFixed(2)} MB</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>File Storage</CardTitle>
                <CardDescription>File-based storage breakdown</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {Object.entries(storageStats.file_stats).map(([category, stats]) => (
                    <div key={category} className="flex items-center justify-between">
                      <span className="text-sm capitalize">{category}</span>
                      <div className="text-right">
                        <div className="font-semibold">{stats.file_count} files</div>
                        <div className="text-xs text-muted-foreground">{stats.size_mb.toFixed(2)} MB</div>
                      </div>
                    </div>
                  ))}
                  <hr className="my-2" />
                  <div className="flex items-center justify-between font-semibold">
                    <span>Total Storage</span>
                    <span>{storageStats.total_storage.size_mb.toFixed(2)} MB</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default Analytics;