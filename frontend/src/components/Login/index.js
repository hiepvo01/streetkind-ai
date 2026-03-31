import React, { useState } from 'react';
import {
    Button,
    Grid,
    Segment,
    Form,
    Header,
    Icon,
    Image,
    Message,
} from 'semantic-ui-react';
import { useAuth } from '../../context/AuthContext';

const Login = () => {
    const { login } = useAuth();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState(null);
    const [submitting, setSubmitting] = useState(false);

    const handleSubmit = async () => {
        setError(null);
        setSubmitting(true);
        try {
            await login(email, password);
        } catch (err) {
            setError(err.message);
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <Grid
            className='loginGrid'
            container
            centered
            verticalAlign='middle'
        >
            <Grid.Column mobile={16} tablet={12} computer={6}>
                <Segment padded color='blue' raised>
                    <Image src='/street-kind-logo-black.svg' centered size='medium' />
                    <Header as='h2' textAlign='center'>
                        Safe Base & Incident Report Login
                    </Header>
                    {error && <Message error visible content={error} />}
                    <Form onSubmit={handleSubmit}>
                        <Form.Input
                            label='Email:'
                            placeholder='Email Address'
                            type='text'
                            required
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                        />
                        <Form.Input
                            label='Password:'
                            placeholder='Password'
                            type='password'
                            required
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                        />
                        <Grid>
                            <Grid.Row columns={2}>
                                <Grid.Column verticalAlign='middle'>
                                    <a
                                        className='forgotPasswordLink'
                                        href='/forgotPassword'
                                        onClick={(e) => e.preventDefault()}
                                    >
                                        Forgot Password?
                                    </a>
                                </Grid.Column>
                                <Grid.Column>
                                    <Button
                                        icon
                                        floated='right'
                                        labelPosition='right'
                                        color='green'
                                        type='submit'
                                        disabled={submitting}
                                        loading={submitting}
                                    >
                                        Login
                                        <Icon name='sign in' />
                                    </Button>
                                </Grid.Column>
                            </Grid.Row>
                        </Grid>
                    </Form>
                </Segment>
            </Grid.Column>
        </Grid>
    );
};

export default Login;
