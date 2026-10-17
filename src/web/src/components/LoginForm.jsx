import LocalizedText from "./Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../lib/interfaceLocale";
import { getApiErrorMessage } from '../lib/apiErrorMessages';
import Footer from './Shared/Footer';
import TooltipButton from './Shared/TooltipButton';
import brandLogo from '../assets/brand/slskdn-logo-lockup.png';
import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Checkbox,
  Form,
  Grid,
  Header,
  Icon,
  Input,
  Message,
  Segment,
} from 'semantic-ui-react';

const initialState = {
  password: '',
  rememberMe: true,
  username: '',
};

export const getHttpsHintUrl = (location) => {
  if (!location) {
    return null;
  }

  const { hostname, protocol } = location;

  if (!hostname || protocol === 'https:') {
    return null;
  }

  return `https://${hostname}:5031`;
};

const LoginForm = ({ error, loading, onLoginAttempt }) => {
  useInterfaceLanguage();
  const usernameInput = useRef();
  const [state, setState] = useState(initialState);
  const [ready, setReady] = useState(false);
  const httpsUrl = useMemo(() => {
    if (typeof window === 'undefined') {
      return null;
    }

    return getHttpsHintUrl(window.location);
  }, []);

  useEffect(() => {
    if (state.username !== '' && state.password !== '') {
      setReady(true);
    } else {
      setReady(false);
    }
  }, [state]);

  useEffect(() => {
    usernameInput.current?.focus();
  }, [loading]);

  const handleChange = (field, value) => {
    setState({
      ...state,
      [field]: value,
    });
  };

  const { password, rememberMe, username } = state;

  return (
    <>
      <Grid
        style={{ height: 'calc(100vh - 40px)' }}
        textAlign="center"
        verticalAlign="middle"
      >
        <Grid.Column style={{ maxWidth: 520 }}>
          <Header
            as="h2"
            className="login-brand"
            textAlign="center"
          >
            <img
              alt={interfaceText("slskdN")}
              className="login-brand-logo"
              src={brandLogo}
             {...interfaceTextProps("slskdN")}/>
          </Header>
          <Form size="large">
            <Segment raised>
              <Input
                data-testid="login-username"
                disabled={loading}
                fluid
                icon="user"
                iconPosition="left"
                onChange={(event) =>
                  handleChange('username', event.target.value)
                }
                placeholder={interfaceText("Username")}
                ref={usernameInput}
               {...interfaceTextProps("Username")}/>
              <Form.Input
                data-testid="login-password"
                disabled={loading}
                fluid
                icon="lock"
                iconPosition="left"
                onChange={(event) =>
                  handleChange('password', event.target.value)
                }
                placeholder={interfaceText("Password")}
                type="password"
               {...interfaceTextProps("Password")}/>
              <Checkbox
                checked={rememberMe}
                disabled={loading}
                label={interfaceText("Remember Me")}
                onChange={() => handleChange('rememberMe', !rememberMe)}
               {...interfaceTextProps("Remember Me")}/>
            </Segment>
            <TooltipButton
              className="login-button"
              data-testid="login-submit"
              disabled={!ready || loading}
              fluid
              loading={loading}
              onClick={() => onLoginAttempt(username, password, rememberMe)}
              primary
              size="large"
              tooltip="Sign in with these credentials to open your authenticated dashboard."
              type="button"
            >
              <Icon name="sign in" />
              <LocalizedText source={"Login"} /></TooltipButton>
            {error && (
              <Message
                className="login-failure"
                floating
                negative
              >
                <Icon name="x" />
                {getApiErrorMessage(error, { t: interfaceText })}
              </Message>
            )}
            {httpsUrl && (
              <Message
                icon
                info
                size="small"
              >
                <Icon name="shield alternate" />
                <Message.Content>
                  <Message.Header><LocalizedText source={"HTTPS Option"} /></Message.Header>
                  <LocalizedText source={"If your instance exposes TLS, sign in securely at"} />{' '}
                  <a href={httpsUrl}>{httpsUrl}</a>.
                </Message.Content>
              </Message>
            )}
          </Form>
        </Grid.Column>
      </Grid>
      <Footer />
    </>
  );
};

export default LoginForm;
