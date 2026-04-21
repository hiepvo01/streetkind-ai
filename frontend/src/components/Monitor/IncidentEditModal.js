import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { Button, Icon, Loader, Message, Modal, Segment } from 'semantic-ui-react';

import { fetchIncidentFull, updateIncident } from '../../services/api';
import IncidentForm from '../forms/IncidentForm';

const IncidentEditModal = ({
    open,
    onClose,
    formId,
    sites,
    incidentFieldOptions,
    onSaved,
}) => {
    const [editFormData, setEditFormData] = useState(null);
    const [editLoading, setEditLoading] = useState(false);
    const [editError, setEditError] = useState(null);
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        if (!open || !formId) {
            setEditFormData(null);
            setEditError(null);
            return;
        }
        let cancelled = false;
        (async () => {
            setEditLoading(true);
            setEditError(null);
            setEditFormData(null);
            try {
                const data = await fetchIncidentFull(formId);
                if (!cancelled) setEditFormData(data);
            } catch (e) {
                if (!cancelled) setEditError(e.message);
            } finally {
                if (!cancelled) setEditLoading(false);
            }
        })();
        return () => { cancelled = true; };
    }, [open, formId]);

    const handleSaveEdit = async (status) => {
        if (!editFormData || !formId) return;
        setSaving(true);
        setEditError(null);
        try {
            await updateIncident(formId, editFormData, status);
            onClose();
            onSaved?.();
        } catch (e) {
            setEditError(e.message);
        } finally {
            setSaving(false);
        }
    };

    const handleClose = () => {
        setEditFormData(null);
        setEditError(null);
        onClose();
    };

    return (
        <Modal
            open={open}
            onClose={handleClose}
            size='large'
            closeIcon
        >
            <Modal.Header>
                <Icon name='edit' />
                Edit Incident Report
            </Modal.Header>
            <Modal.Content scrolling>
                {editLoading && (
                    <Segment basic>
                        <Loader active inline='centered' content='Loading incident...' />
                    </Segment>
                )}
                {editError && (
                    <Message error>
                        <Icon name='warning circle' />
                        {editError}
                    </Message>
                )}
                {editFormData && !editLoading && (
                    <IncidentForm
                        data={editFormData}
                        onChange={setEditFormData}
                        fieldOptions={incidentFieldOptions}
                        sites={sites}
                    />
                )}
            </Modal.Content>
            <Modal.Actions>
                <Button
                    color='green'
                    onClick={() => handleSaveEdit('completed')}
                    disabled={saving || editLoading || !editFormData}
                    loading={saving}
                    icon='check'
                    labelPosition='left'
                    content='Save as Completed'
                />
                <Button
                    color='yellow'
                    onClick={() => handleSaveEdit('draft')}
                    disabled={saving || editLoading || !editFormData}
                    loading={saving}
                    icon='save outline'
                    labelPosition='left'
                    content='Save as Draft'
                />
                <Button
                    onClick={handleClose}
                    disabled={saving}
                    content='Cancel'
                />
            </Modal.Actions>
        </Modal>
    );
};

IncidentEditModal.propTypes = {
    open: PropTypes.bool.isRequired,
    onClose: PropTypes.func.isRequired,
    formId: PropTypes.string,
    sites: PropTypes.array.isRequired,
    incidentFieldOptions: PropTypes.object.isRequired,
    onSaved: PropTypes.func,
};

export default IncidentEditModal;
