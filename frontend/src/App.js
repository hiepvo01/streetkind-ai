import React, { useState, useEffect } from 'react';
import { Sidebar, Loader, Segment } from 'semantic-ui-react';

import { fetchConfig } from './services/api';
import { useAuth } from './context/AuthContext';
import MenuBar from './components/MenuBar';
import NavSidebar from './components/NavSidebar';
import FormSelector from './components/FormSelector';
import VoiceInput from './components/VoiceInput';
import FormPreview from './components/FormPreview';
import Dashboard from './components/Dashboard';
import Monitor from './components/Monitor';
import Login from './components/Login';

const App = () => {
    const { user, loading } = useAuth();
    const [config, setConfig] = useState(null);
    const [sidebarVisible, setSidebarVisible] = useState(false);
    const [currentView, setCurrentView] = useState('forms'); // 'forms', 'dashboard', or 'monitor'
    const [formType, setFormType] = useState(null);
    const [site, setSite] = useState(null);
    const [transcript, setTranscript] = useState('');
    const [extractedData, setExtractedData] = useState(null);
    const [submitted, setSubmitted] = useState(false);

    useEffect(() => {
        fetchConfig().then((cfg) => {
            setConfig(cfg);
            setFormType(cfg.default_form_type);
            setSite(cfg.default_site);
        });
    }, []);

    const toggleSidebar = () => setSidebarVisible(!sidebarVisible);

    const handleReset = () => {
        setTranscript('');
        setExtractedData(null);
        setSubmitted(false);
    };

    const handleSelectFormType = (type) => {
        setCurrentView('forms');
        setFormType(type);
        handleReset();
    };

    const handleShowDashboard = () => {
        setCurrentView('dashboard');
    };

    const handleShowMonitor = () => {
        setCurrentView('monitor');
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
                    onShowMonitor={handleShowMonitor}
                />
                <Sidebar.Pusher>
                    <div className='main-content'>
                        {currentView === 'dashboard' ? (
                            <Dashboard />
                        ) : currentView === 'monitor' ? (
                            <Monitor />
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
                                    onSelectSite={setSite}
                                />
                                <VoiceInput
                                    speechConfig={config.speech_recognition}
                                    transcript={transcript}
                                    onTranscriptChange={setTranscript}
                                    formType={formType}
                                    site={site}
                                    onExtracted={setExtractedData}
                                    submitted={submitted}
                                />
                                {extractedData && !submitted && (
                                    <FormPreview
                                        formType={formType}
                                        data={extractedData}
                                        onDataChange={setExtractedData}
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
