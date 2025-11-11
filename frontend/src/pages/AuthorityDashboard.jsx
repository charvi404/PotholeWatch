import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { LogOut, Filter, CheckCircle, Send } from 'lucide-react';
import { toast } from 'sonner';
import api from '../services/api';
import { MapContainer, TileLayer, Marker, Popup, CircleMarker } from 'react-leaflet';

const AuthorityDashboard = ({ user, onLogout }) => {
  const [reports, setReports] = useState([]);
  const [filteredReports, setFilteredReports] = useState([]);
  const [selectedReport, setSelectedReport] = useState(null);
  const [filterSeverity, setFilterSeverity] = useState('all');
  const [filterStatus, setFilterStatus] = useState('all');
  const [actionNotes, setActionNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  useEffect(() => {
    loadReports();
  }, []);

  useEffect(() => {
    applyFilters();
  }, [reports, filterSeverity, filterStatus]);

  const loadReports = async () => {
    try {
      const data = await api.getAllPotholes();
      setReports(data);
    } catch (error) {
      toast.error('Failed to load reports');
    }
  };

  const applyFilters = () => {
    let filtered = [...reports];
    if (filterSeverity !== 'all') {
      filtered = filtered.filter(r => r.severity === filterSeverity);
    }
    if (filterStatus !== 'all') {
      filtered = filtered.filter(r => r.status === filterStatus);
    }
    setFilteredReports(filtered);
  };

  const handleAssignDrone = async (potholeId) => {
    setLoading(true);
    try {
      await api.assignDrone(potholeId);
      toast.success('Drone assigned successfully');
      loadReports();
    } catch (error) {
      toast.error('Failed to assign drone');
    } finally {
      setLoading(false);
    }
  };

  const getMarkerColor = (status) => {
    if (status === 'Pending') return 'red';
    if (status === 'In Progress') return 'yellow';
    if (status === 'Resolved') return 'green';
    return 'red';
  };

  const handleAction = async (potholeId, action) => {
    setLoading(true);
    try {
      await api.potholeAction(potholeId, action, actionNotes);
      toast.success(`Action ${action} recorded successfully`);
      setActionNotes('');
      setIsDialogOpen(false);
      loadReports();
    } catch (error) {
      toast.error('Action failed');
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    const statusMap = {
      'Pending': { color: 'bg-yellow-100 text-yellow-800', text: 'Pending' },
      'Reported': { color: 'bg-blue-100 text-blue-800', text: 'Reported' },
      'Inspected': { color: 'bg-purple-100 text-purple-800', text: 'Inspected' },
      'In Progress': { color: 'bg-pink-100 text-pink-800', text: 'In Progress' },
      'Resolved': { color: 'bg-green-100 text-green-800', text: 'Resolved' }
    };
    const config = statusMap[status] || statusMap['Pending'];
    return <Badge className={config.color}>{config.text}</Badge>;
  };

  const getSeverityBadge = (severity) => {
    const severityMap = {
      'Minor': 'bg-green-100 text-green-800',
      'Moderate': 'bg-yellow-100 text-yellow-800',
      'Severe': 'bg-orange-100 text-orange-800',
      'Critical': 'bg-red-100 text-red-800'
    };
    return <Badge className={severityMap[severity]}>{severity}</Badge>;
  };

  const stats = {
    total: reports.length,
    pending: reports.filter(r => r.status === 'Pending' || r.status === 'Reported').length,
    inProgress: reports.filter(r => r.status === 'In Progress' || r.status === 'Inspected').length,
    resolved: reports.filter(r => r.status === 'Resolved').length
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50">
      {/* Header */}
      <nav className="bg-white border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div>
              <h1 className="text-xl font-bold text-gray-900">Authority Dashboard</h1>
              <p className="text-sm text-gray-500">Welcome, {user.name}</p>
            </div>
            <Button variant="outline" onClick={onLogout} data-testid="authority-logout-btn">
              <LogOut className="w-4 h-4 mr-2" />
              Logout
            </Button>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 mb-8">
          <Card>
            <CardContent className="pt-6">
              <div className="text-2xl font-bold text-blue-600" data-testid="stat-total">{stats.total}</div>
              <p className="text-sm text-gray-500">Total Reports</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="text-2xl font-bold text-yellow-600" data-testid="stat-pending">{stats.pending}</div>
              <p className="text-sm text-gray-500">Pending</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="text-2xl font-bold text-purple-600" data-testid="stat-in-progress">{stats.inProgress}</div>
              <p className="text-sm text-gray-500">In Progress</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="text-2xl font-bold text-green-600" data-testid="stat-resolved">{stats.resolved}</div>
              <p className="text-sm text-gray-500">Resolved</p>
            </CardContent>
          </Card>
        </div>
        {/* Pothole Map - move outside the grid, make it full width */}
        <Card className="mb-8 w-full">
          <CardHeader>
            <CardTitle>Pothole Map</CardTitle>
            <CardDescription>All potholes shown as markers</CardDescription>
          </CardHeader>
          <CardContent className="w-full">
            <div style={{ height: '600px', width: '100%' }} className="w-full">
              <MapContainer
                center={[18.5204, 73.8567]}
                zoom={12}
                style={{ height: '100%', width: '100%' }}
                className="w-full"
              >
                <TileLayer
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                />
                {filteredReports.map((pothole) => {
                  let markerColor = 'red';
                  if (pothole.drone_status === 'in_progress' || pothole.status === 'In Progress') {
                    markerColor = 'yellow';
                  } else if (pothole.status === 'Resolved' || pothole.status === 'Inspected') {
                    markerColor = 'green';
                  }
                  return (
                    <CircleMarker
                      key={pothole.id}
                      center={[pothole.coordinates.lat, pothole.coordinates.lng]}
                      radius={12}
                      color={markerColor}
                      fillOpacity={0.7}
                    >
                      <Popup>
                        <div className="text-sm">
                          <p className="font-semibold">{pothole.location}</p>
                          <p>Severity: {pothole.severity}</p>
                          <p>Estimated Cost: ₹{pothole.estimated_cost_inr}</p>
                          <Button
                            size="sm"
                            className="bg-blue-600 hover:bg-blue-700 mt-2"
                            onClick={() => handleAssignDrone(pothole.id)}
                            disabled={loading || pothole.status !== 'Pending'}
                          >
                            Assign Drone
                          </Button>
                        </div>
                      </Popup>
                    </CircleMarker>
                  );
                })}
              </MapContainer>
            </div>
            <div className="flex gap-4 mt-3 text-sm text-gray-600 justify-center w-full">
              <span className="flex items-center gap-1">
                <span className="w-3 h-3 bg-red-500 rounded-full"></span> Pending
              </span>
              <span className="flex items-center gap-1">
                <span className="w-3 h-3 bg-yellow-400 rounded-full"></span> In Progress
              </span>
              <span className="flex items-center gap-1">
                <span className="w-3 h-3 bg-green-500 rounded-full"></span> Resolved
              </span>
            </div>
          </CardContent>
        </Card>
        {/* Filters */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Filter className="w-5 h-5" />
              Filters
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex gap-4">
              <div className="flex-1">
                <Select value={filterSeverity} onValueChange={setFilterSeverity}>
                  <SelectTrigger data-testid="filter-severity">
                    <SelectValue placeholder="All Severities" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Severities</SelectItem>
                    <SelectItem value="Minor">Minor</SelectItem>
                    <SelectItem value="Moderate">Moderate</SelectItem>
                    <SelectItem value="Severe">Severe</SelectItem>
                    <SelectItem value="Critical">Critical</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex-1">
                <Select value={filterStatus} onValueChange={setFilterStatus}>
                  <SelectTrigger data-testid="filter-status">
                    <SelectValue placeholder="All Statuses" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Statuses</SelectItem>
                    <SelectItem value="Pending">Pending</SelectItem>
                    <SelectItem value="Reported">Reported</SelectItem>
                    <SelectItem value="Inspected">Inspected</SelectItem>
                    <SelectItem value="In Progress">In Progress</SelectItem>
                    <SelectItem value="Resolved">Resolved</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Reports List */}
        <Card>
          <CardHeader>
            <CardTitle>Pothole Reports</CardTitle>
            <CardDescription>{filteredReports.length} reports</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4" data-testid="authority-reports-list">
              {filteredReports.length === 0 ? (
                <p className="text-center text-gray-500 py-8">No reports found</p>
              ) : (
                filteredReports
                  .filter(report => {
                    // If filterStatus is 'all', show all
                    if (filterStatus === 'all') return true;
                    // If filterStatus is 'In Progress', show both 'In Progress' and drone-assigned
                    if (filterStatus === 'In Progress') {
                      return report.status === 'In Progress' || report.drone_status === 'in_progress';
                    }
                    // Otherwise, match status
                    return report.status === filterStatus;
                  })
                  .map((report) => (
                    <div
                      key={report.id}
                      className="border rounded-lg p-4 hover:bg-gray-50 transition-colors cursor-pointer"
                      onClick={() => {
                        setSelectedReport(report);
                        setIsDialogOpen(true);
                      }}
                      data-testid={`authority-report-${report.id}`}
                    >
                      <div className="flex justify-between items-start mb-3">
                        <div className="flex-1">
                          <h3 className="font-semibold text-lg">{report.location}</h3>
                          <p className="text-sm text-gray-500">
                            Reported: {new Date(report.created_at).toLocaleString()}
                          </p>
                        </div>
                        <div className="flex gap-2">
                          {getSeverityBadge(report.severity)}
                          {getStatusBadge(report.status)}
                        </div>
                      </div>
                      <div className="grid grid-cols-4 gap-4 text-sm">
                        <div>
                          <p className="text-gray-500">Potholes</p>
                          <p className="font-semibold">{report.pothole_count}</p>
                        </div>
                        <div>
                          <p className="text-gray-500">Area</p>
                          <p className="font-semibold">{report.total_area_m2} m²</p>
                        </div>
                        <div>
                          <p className="text-gray-500">Material</p>
                          <p className="font-semibold">{report.bags_required} bags</p>
                        </div>
                        <div>
                          <p className="text-gray-500">Cost</p>
                          <p className="font-semibold text-blue-600">₹{report.estimated_cost_inr}</p>
                        </div>
                      </div>
                    </div>
                  ))
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Detail Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          {selectedReport && (
            <>
              <DialogHeader>
                <DialogTitle className="flex items-center justify-between">
                  <span>{selectedReport.location}</span>
                  <div className="flex gap-2">
                    {getSeverityBadge(selectedReport.severity)}
                    {getStatusBadge(selectedReport.status)}
                  </div>
                </DialogTitle>
                <DialogDescription>
                  Report ID: {selectedReport.id}
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-4">
                {/* Images */}
                {selectedReport.processed_image_url && (
                  <div>
                    <h4 className="font-semibold mb-2">Detection Image</h4>
                    <img
                      src={`${process.env.REACT_APP_BACKEND_URL}${selectedReport.processed_image_url}`}
                      alt="Processed"
                      className="w-full rounded-lg border"
                      data-testid="processed-image"
                    />
                  </div>
                )}

                {/* Details Grid */}
                <div className="grid grid-cols-2 gap-4 p-4 bg-gray-50 rounded-lg">
                  <div>
                    <p className="text-sm text-gray-500">Pothole Count</p>
                    <p className="text-xl font-bold">{selectedReport.pothole_count}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Total Area</p>
                    <p className="text-xl font-bold">{selectedReport.total_area_m2} m²</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Confidence</p>
                    <p className="text-xl font-bold">{selectedReport.confidence}%</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Material</p>
                    <p className="text-lg font-semibold">{selectedReport.material}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Bags Required</p>
                    <p className="text-xl font-bold">{selectedReport.bags_required}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Estimated Cost</p>
                    <p className="text-xl font-bold text-blue-600">₹{selectedReport.estimated_cost_inr}</p>
                  </div>
                </div>

                {/* Timeline */}
                <div>
                  <h4 className="font-semibold mb-3">Audit Trail</h4>
                  <div className="space-y-2">
                    {selectedReport.audit?.map((entry, idx) => (
                      <div key={idx} className="flex items-start gap-3 p-3 bg-gray-50 rounded">
                        <div className="w-2 h-2 rounded-full bg-blue-500 mt-2"></div>
                        <div className="flex-1">
                          <p className="font-medium">{entry.action.replace(/_/g, ' ').toUpperCase()}</p>
                          {entry.notes && <p className="text-sm text-gray-600">{entry.notes}</p>}
                          <p className="text-xs text-gray-400 mt-1">
                            {new Date(entry.timestamp).toLocaleString()}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Action Section */}
                <div className="border-t pt-4">
                  <h4 className="font-semibold mb-3">Take Action</h4>
                  <Textarea
                    placeholder="Add notes (optional)"
                    value={actionNotes}
                    onChange={(e) => setActionNotes(e.target.value)}
                    className="mb-3"
                    data-testid="action-notes-input"
                  />
                  <div className="grid grid-cols-2 gap-2">
                    <Button
                      onClick={() => handleAction(selectedReport.id, 'dispatch_drone')}
                      disabled={loading}
                      variant="outline"
                      data-testid="action-dispatch-drone"
                    >
                      Dispatch Drone
                    </Button>
                    <Button
                      onClick={() => handleAction(selectedReport.id, 'inspection_done')}
                      disabled={loading}
                      variant="outline"
                      data-testid="action-inspection-done"
                    >
                      Mark Inspected
                    </Button>
                    <Button
                      onClick={() => handleAction(selectedReport.id, 'schedule_repair')}
                      disabled={loading}
                      className="bg-purple-600 hover:bg-purple-700"
                      data-testid="action-schedule-repair"
                    >
                      Schedule Repair
                    </Button>
                    <Button
                      onClick={() => handleAction(selectedReport.id, 'repair_done')}
                      disabled={loading}
                      className="bg-green-600 hover:bg-green-700"
                      data-testid="action-repair-done"
                    >
                      <CheckCircle className="w-4 h-4 mr-2" />
                      Mark Repaired
                    </Button>
                  </div>
                </div>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default AuthorityDashboard;
