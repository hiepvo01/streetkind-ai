import React, { useState, useEffect } from 'react';
import { Sidebar, Loader, Segment } from 'semantic-ui-react';

import { fetchConfig } from './services/api';
import MenuBar from './components/MenuBar';
import NavSidebar from './components/NavSidebar';
import FormSelector from './components/FormSelector';
import VoiceInput from './components/VoiceInput';
import FormPreview from './components/FormPreview';

const App = () => {
    const [config, setConfig] = useState(null);
    const [sidebarVisible, setSidebarVisible] = useState(false);
    const [formType, setFormType] = useState(null);
    const [site, setSite] = useState(null);
    const [transcript, setTranscript] = useState('');
    const [extractedData, setExtractedData] = useState(null);
    const [submitted, setSubmitted] = useState(false);

    // Load config from backend on mount
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
                    activeFormType={formType}
                    onSelectFormType={(type) => { setFormType(type); handleReset(); }}
                />
                <Sidebar.Pusher>
                    <div className='main-content'>
                        <FormSelector
                            appName={config.app_name}
                            appSubtitle={config.app_subtitle}
                            formTypes={config.form_types}
                            activeFormType={formType}
                            onSelectFormType={(type) => { setFormType(type); handleReset(); }}
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
                            />
                        )}
                    </div>
                </Sidebar.Pusher>
            </Sidebar.Pushable>
        </div>
    );
};

export default App;
