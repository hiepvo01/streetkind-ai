import React, { useState, useEffect } from 'react';
import { Sidebar, Loader, Segment } from 'semantic-ui-react';

import { fetchConfig } from './services/api';
import { createEmptyIncidentFormData, createEmptySafeBaseFormData } from './utils/initialFormData';
import { useAuth } from './context/AuthContext';
import MenuBar from './components/MenuBar';
import NavSidebar from './components/NavSidebar';
import FormSelector from './components/FormSelector';
import VoiceInput from './components/VoiceInput';
import FormPreview from './components/FormPreview';
import Dashboard from './components/Dashboard';
import Monitor from './components/Monitor';
import MyIncidents from './components/MyIncidents';
import Login from './components/Login';

const App = () => {
    const { user, profile, loading } = useAuth();
    const [config, setConfig] = useState(null);
    const [sidebarVisible, setSidebarVisible] = useState(false);
    const [currentView, setCurrentView] = useState('forms'); // 'forms' | 'dashboard' | 'myIncidents' | 'monitor'
    const [formType, setFormType] = useState(null);
    const [site, setSite] = useState(null);
    const [transcript, setTranscript] = useState('');
    const [formData, setFormData] = useState(null);
    const [submitted, setSubmitted] = useState(false);

    const showMonitorNav = profile?.userLevel === 'administrator' || profile?.userLevel === 'teamLeader';

    useEffect(() => {
        fetchConfig().then((cfg) => {
            setConfig(cfg);
            setFormType(cfg.default_form_type);
            setSite(cfg.default_site);
            setFormData(
                cfg.default_form_type === 'safebase'
                    ? createEmptySafeBaseFormData(cfg.default_site || '')
                    : createEmptyIncidentFormData(cfg.default_site || '')
            );
        });
    }, []);

    useEffect(() => {
        if (!showMonitorNav && currentView === 'monitor') {
            setCurrentView('myIncidents');
        }
    }, [showMonitorNav, currentView]);

    const toggleSidebar = () => setSidebarVisible(!sidebarVisible);

    const handleReset = () => {
        setTranscript('');
        setSubmitted(false);
        setFormData(
            formType === 'safebase'
                ? createEmptySafeBaseFormData(site || '')
                : createEmptyIncidentFormData(site || '')
        );
    };

    const handleSelectFormType = (type) => {
        setCurrentView('forms');
        setFormType(type);
        setTranscript('');
        setSubmitted(false);
        setFormData(
            type === 'safebase'
                ? createEmptySafeBaseFormData(site || '')
                : createEmptyIncidentFormData(site || '')
        );
    };

    const handleSelectSite = (newSite) => {
        setSite(newSite);
        setFormData((prev) => {
            if (!prev) return prev;
            if (formType === 'incident') {
                return { ...prev, incident: { ...prev.incident, site: newSite } };
            }
            return { ...prev, site: newSite };
        });
    };

    const handleShowDashboard = () => {
        setCurrentView('dashboard');
    };

    const handleShowMonitor = () => {
        setCurrentView('monitor');
    };

    const handleShowMyIncidents = () => {
        setCurrentView('myIncidents');
    };

    if (loading) {
        return (
            <Segment basic style={{ minHeight: '100vh' }}>
                <Loader active size='large' content='Loading...' />
            </Segment>
        );
    }

    if (!user) {
        return <Login />;
    }

    if (!config) {
        return (
            <Segment basic style={{ minHeight: '100vh' }}>
                <Loader active size='large' content='Loading...' />
            </Segment>
        );
    }

    return (
        <div>
            <MenuBar
                appName={config.app_name}
                onToggleSidebar={toggleSidebar}
            />
            <Sidebar.Pushable attached='bottom'>
                <NavSidebar
                    visible={sidebarVisible}
                    onToggle={toggleSidebar}
                    formTypes={config.form_types}
                    activeFormType={currentView === 'forms' ? formType : null}
                    onSelectFormType={handleSelectFormType}
                    currentView={currentView}
                    onShowDashboard={handleShowDashboard}
                    onShowMyIncidents={handleShowMyIncidents}
                    onShowMonitor={handleShowMonitor}
                    showMonitor={showMonitorNav}
                />
                <Sidebar.Pusher>
                    <div className='main-content'>
                        {currentView === 'dashboard' ? (
                            <Dashboard />
                        ) : currentView === 'myIncidents' ? (
                            <MyIncidents sites={config.sites} fieldOptions={config.field_options} />
                        ) : currentView === 'monitor' ? (
                            <Monitor sites={config.sites} fieldOptions={config.field_options} />
                        ) : (
                            <>
                                <FormSelector
                                    appName={config.app_name}
                                    appSubtitle={config.app_subtitle}
                                    formTypes={config.form_types}
                                    activeFormType={formType}
                                    onSelectFormType={handleSelectFormType}
                                    sites={config.sites}
                                    activeSite={site}
                                    onSelectSite={handleSelectSite}
                                />
                                <VoiceInput
                                    speechConfig={config.speech_recognition}
                                    transcript={transcript}
                                    onTranscriptChange={setTranscript}
                                    formType={formType}
                                    site={site}
                                    onExtracted={setFormData}
                                    submitted={submitted}
                                />
                                {formData && !submitted && (
                                    <FormPreview
                                        formType={formType}
                                        data={formData}
                                        onDataChange={setFormData}
                                        onSubmitted={() => setSubmitted(true)}
                                        onReset={handleReset}
                                        fieldOptions={config.field_options}
                                        sites={config.sites}
                                    />
                                )}
                            </>
                        )}
                    </div>
                </Sidebar.Pusher>
            </Sidebar.Pushable>
        </div>
    );
};

export default App;
