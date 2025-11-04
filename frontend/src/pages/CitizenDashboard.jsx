import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import { Upload, MapPin, LogOut, Image as ImageIcon, TrendingUp } from 'lucide-react';
import { toast } from 'sonner';
import api from '../services/api';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

// Fix leaflet icon issue
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

const CitizenDashboard = ({ user, onLogout }) => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [location, setLocation] = useState('');
  const [coordinates, setCoordinates] = useState({ lat: 18.5204, lng: 73.8567 });
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadReports();
  }, []);

  const loadReports = async () => {
    try {
      const data = await api.getUserReports(user.id);
      setReports(data);
    } catch (error) {
      toast.error('Failed to load reports');
    }
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (file.size > 10 * 1024 * 1024) {
        toast.error('File size must be less than 10MB');
        return;
      }
      setSelectedFile(file);
      const url = URL.createObjectURL(file);
      setPreviewUrl(url);
    }
  };

  const autoDetectLocation = () => {
    if (navigator.geolocation) {
      toast.info('Detecting location...');
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const coords = {
            lat: position.coords.latitude,
            lng: position.coords.longitude
          };
          setCoordinates(coords);
          setLocation(`Lat: ${coords.lat.toFixed(4)}, Lng: ${coords.lng.toFixed(4)}`);
          toast.success('Location detected!');
        },
        (error) => {
          toast.error('Could not detect location. Please enter manually.');
        }
      );
    } else {
      toast.error('Geolocation is not supported by your browser');
    }
  };

  const handleAnalyze = async () => {
    if (!selectedFile) {
      toast.error('Please select an image');
      return;
    }
    if (!location) {
      toast.error('Please provide location');
      return;
    }

    setIsAnalyzing(true);
    try {
      const result = await api.analyzePothole(selectedFile, location, coordinates);
      setAnalysisResult(result);
      toast.success('Analysis complete!');
      loadReports();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Analysis failed');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleNotify = async (potholeId) => {
    setLoading(true);
    try {
      await api.notifyAuthorities(potholeId);
      toast.success('Authorities notified!');
      loadReports();
    } catch (error) {
      toast.error('Notification failed');
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
    setAnalysisResult(null);
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
    return <Badge className={config.color} data-testid={`status-badge-${status.toLowerCase().replace(' ', '-')}`}>{config.text}</Badge>;
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

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-green-50">
      {/* Header */}
      <nav className="bg-white border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div>
              <h1 className="text-xl font-bold text-gray-900">Citizen Dashboard</h1>
              <p className="text-sm text-gray-500">Welcome, {user.name}</p>
            </div>
            <Button variant="outline" onClick={onLogout} data-testid="logout-btn">
              <LogOut className="w-4 h-4 mr-2" />
              Logout
            </Button>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="grid lg:grid-cols-2 gap-8">
          {/* Upload Section */}
          <div className="space-y-6">
            <Card data-testid="upload-card">
              <CardHeader>
                <CardTitle>Report a Pothole</CardTitle>
                <CardDescription>Upload an image and detect potholes instantly</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* File Upload */}
                <div>
                  <Label>Upload Image</Label>
                  <div className="mt-2">
                    <input
                      type="file"
                      accept="image/*"
                      onChange={handleFileSelect}
                      className="hidden"
                      id="file-upload"
                      data-testid="file-input"
                    />
                    <label
                      htmlFor="file-upload"
                      className="flex items-center justify-center w-full h-32 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-blue-500 transition-colors"
                    >
                      {previewUrl ? (
                        <img src={previewUrl} alt="Preview" className="h-full object-contain" />
                      ) : (
                        <div className="text-center">
                          <Upload className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                          <span className="text-sm text-gray-500">Click to upload</span>
                        </div>
                      )}
                    </label>
                  </div>
                </div>

                {/* Location */}
                <div>
                  <Label>Location</Label>
                  <div className="flex gap-2 mt-2">
                    <Input
                      placeholder="Enter location or address"
                      value={location}
                      onChange={(e) => setLocation(e.target.value)}
                      data-testid="location-input"
                    />
                    <Button onClick={autoDetectLocation} variant="outline" data-testid="auto-detect-btn">
                      <MapPin className="w-4 h-4" />
                    </Button>
                  </div>
                </div>

                <Button
                  onClick={handleAnalyze}
                  disabled={isAnalyzing}
                  className="w-full bg-blue-600 hover:bg-blue-700"
                  data-testid="analyze-btn"
                >
                  {isAnalyzing ? 'Analyzing...' : 'Analyze Pothole'}
                </Button>
              </CardContent>
            </Card>

            {/* Analysis Result */}
            {analysisResult && (
              <Card className="border-blue-200" data-testid="analysis-result-card">
                <CardHeader>
                  <CardTitle className="flex items-center justify-between">
                    <span>Analysis Results</span>
                    {getSeverityBadge(analysisResult.severity)}
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm text-gray-500">Pothole Count</p>
                      <p className="text-2xl font-bold" data-testid="pothole-count">{analysisResult.pothole_count}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">Total Area</p>
                      <p className="text-2xl font-bold" data-testid="total-area">{analysisResult.total_area_m2} m²</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">Confidence</p>
                      <p className="text-2xl font-bold" data-testid="confidence">{analysisResult.confidence}%</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">Estimated Cost</p>
                      <p className="text-2xl font-bold text-blue-600" data-testid="estimated-cost">₹{analysisResult.estimated_cost_inr}</p>
                    </div>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Material Required</p>
                    <p className="font-semibold">{analysisResult.material} ({analysisResult.bags_required} bags)</p>
                  </div>
                  <Button
                    onClick={() => handleNotify(analysisResult.id)}
                    disabled={loading}
                    className="w-full bg-green-600 hover:bg-green-700"
                    data-testid="notify-authorities-btn"
                  >
                    <TrendingUp className="w-4 h-4 mr-2" />
                    Notify Authorities
                  </Button>
                  <Button onClick={resetForm} variant="outline" className="w-full" data-testid="reset-form-btn">
                    Report Another
                  </Button>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Reports & Map */}
          <div className="space-y-6">
            {/* Map */}
            <Card>
              <CardHeader>
                <CardTitle>Reported Locations</CardTitle>
              </CardHeader>
              <CardContent>
                <div style={{ height: '300px' }} data-testid="map-container">
                  <MapContainer
                    center={[18.5204, 73.8567]}
                    zoom={12}
                    style={{ height: '100%', width: '100%' }}
                  >
                    <TileLayer
                      url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                      attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                    />
                    {reports.map((report) => (
                      <Marker
                        key={report.id}
                        position={[report.coordinates.lat, report.coordinates.lng]}
                      >
                        <Popup>
                          <div className="text-sm">
                            <p className="font-semibold">{report.location}</p>
                            <p>Severity: {report.severity}</p>
                            <p>Status: {report.status}</p>
                          </div>
                        </Popup>
                      </Marker>
                    ))}
                  </MapContainer>
                </div>
              </CardContent>
            </Card>

            {/* Reports List */}
            <Card>
              <CardHeader>
                <CardTitle>My Reports</CardTitle>
                <CardDescription>{reports.length} total reports</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4 max-h-[500px] overflow-y-auto" data-testid="reports-list">
                  {reports.length === 0 ? (
                    <p className="text-gray-500 text-center py-8">No reports yet</p>
                  ) : (
                    reports.map((report) => (
                      <div key={report.id} className="border rounded-lg p-4 hover:bg-gray-50 transition-colors" data-testid={`report-item-${report.id}`}>
                        <div className="flex justify-between items-start mb-2">
                          <div>
                            <p className="font-semibold">{report.location}</p>
                            <p className="text-sm text-gray-500">
                              {new Date(report.created_at).toLocaleDateString()}
                            </p>
                          </div>
                          <div className="flex gap-2">
                            {getSeverityBadge(report.severity)}
                            {getStatusBadge(report.status)}
                          </div>
                        </div>
                        <div className="grid grid-cols-3 gap-2 text-sm">
                          <div>
                            <span className="text-gray-500">Count:</span>
                            <span className="font-semibold ml-1">{report.pothole_count}</span>
                          </div>
                          <div>
                            <span className="text-gray-500">Area:</span>
                            <span className="font-semibold ml-1">{report.total_area_m2}m²</span>
                          </div>
                          <div>
                            <span className="text-gray-500">Cost:</span>
                            <span className="font-semibold ml-1">₹{report.estimated_cost_inr}</span>
                          </div>
                        </div>
                        {/* Timeline */}
                        {report.audit && report.audit.length > 0 && (
                          <div className="mt-3 pt-3 border-t">
                            <p className="text-xs font-semibold text-gray-500 mb-2">Timeline</p>
                            <div className="space-y-1">
                              {report.audit.map((entry, idx) => (
                                <div key={idx} className="text-xs text-gray-600 flex items-center gap-2">
                                  <div className="w-1.5 h-1.5 rounded-full bg-blue-500"></div>
                                  <span>{entry.action.replace(/_/g, ' ')}</span>
                                  <span className="text-gray-400">
                                    {new Date(entry.timestamp).toLocaleString()}
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    ))
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CitizenDashboard;
