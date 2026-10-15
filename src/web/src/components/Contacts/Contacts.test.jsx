import * as identityAPI from '../../lib/identity';
import Contacts from './Contacts';
import QRCode from 'qrcode';
import React from 'react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../../lib/identity', () => ({
  addContactFromDiscovery: vi.fn(),
  addContactFromInvite: vi.fn(),
  getContacts: vi.fn(),
  getNearby: vi.fn(),
  createInvite: vi.fn(),
}));

vi.mock('qrcode', () => ({
  default: {
    toDataURL: vi.fn(),
  },
}));

const renderContacts = () =>
  render(
    <MemoryRouter>
      <Contacts />
    </MemoryRouter>,
  );

describe('Contacts', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    identityAPI.getContacts.mockResolvedValue({ data: [] });
    identityAPI.getNearby.mockResolvedValue({ data: [] });
    identityAPI.createInvite.mockResolvedValue({
      data: {
        friendCode: 'FRIEND-1234',
        inviteLink: 'slskdn://invite/test-invite',
      },
    });
    QRCode.toDataURL.mockResolvedValue('data:image/png;base64,inviteqr');
  });

  afterEach(() => {
    vi.restoreAllMocks();
    delete window.BarcodeDetector;
    delete window.createImageBitmap;
  });

  it('renders a QR code for newly created invites', async () => {
    renderContacts();

    fireEvent.click(await screen.findByText('Create Invite'));

    expect(await screen.findByTestId('contacts-invite-output')).toHaveValue(
      'slskdn://invite/test-invite',
    );
    expect(screen.getByTestId('contacts-invite-qr')).toHaveAttribute(
      'src',
      'data:image/png;base64,inviteqr',
    );
    expect(QRCode.toDataURL).toHaveBeenCalledWith(
      'slskdn://invite/test-invite',
      {
        errorCorrectionLevel: 'M',
        margin: 2,
        scale: 6,
      },
    );
  });

  it('ignores malformed contact and nearby list payloads', async () => {
    identityAPI.getContacts.mockResolvedValue({
      data: [null, { nickname: 'No peer id' }, { nickname: 'Alice', peerId: 'alice-peer' }],
    });
    identityAPI.getNearby.mockResolvedValue({ data: { peers: [] } });

    renderContacts();

    expect(await screen.findByText('Create Invite')).toBeInTheDocument();
    expect(screen.queryByText('contacts.map is not a function')).not.toBeInTheDocument();
    await waitFor(() => expect(identityAPI.getContacts).toHaveBeenCalled());
    expect(screen.queryByText('No peer id')).not.toBeInTheDocument();
  });

  it('shows contact-list failures instead of claiming the list is empty', async () => {
    const user = userEvent.setup();
    identityAPI.getContacts.mockRejectedValueOnce({
      response: { data: { detail: 'Contacts service unavailable', status: 503 } },
    });
    renderContacts();

    expect(await screen.findByTestId('contacts-load-error'))
      .toHaveTextContent('Failed to load contacts.');
    expect(screen.queryByText('No contacts yet')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Retry Contacts' }));

    expect(await screen.findByText('No contacts yet')).toBeInTheDocument();
    expect(identityAPI.getContacts).toHaveBeenCalledTimes(2);
  });

  it('shows nearby discovery failures and retries the request', async () => {
    identityAPI.getNearby
      .mockRejectedValueOnce({
        response: { data: { detail: 'mDNS service unavailable', status: 503 } },
      })
      .mockResolvedValueOnce({
        data: [{ displayName: 'Nearby Alice', endpoint: '192.0.2.4', peerId: 'peer-1' }],
      });

    renderContacts();
    fireEvent.click(await screen.findByText('Nearby'));

    expect(await screen.findByTestId('contacts-nearby-error'))
      .toHaveTextContent('Nearby peer discovery failed.');
    expect(screen.queryByText('No nearby peers found')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Retry Nearby' }));

    expect(await screen.findByText('Nearby Alice')).toBeInTheDocument();
    expect(identityAPI.getNearby).toHaveBeenCalledTimes(2);
  });

  it('adds a nearby peer through an in-app nickname dialog', async () => {
    const user = userEvent.setup();
    identityAPI.getNearby.mockResolvedValue({
      data: [{ displayName: 'Nearby Alice', endpoint: '192.0.2.4', peerId: 'peer-1' }],
    });
    identityAPI.getContacts
      .mockResolvedValueOnce({ data: [] })
      .mockResolvedValueOnce({
        data: [{ id: 'contact-1', nickname: 'Alice', peerId: 'peer-1' }],
      });
    identityAPI.addContactFromDiscovery.mockResolvedValue({ data: {} });
    renderContacts();

    await user.click(await screen.findByText('Nearby'));
    await user.click(await screen.findByRole('button', { name: 'Add Contact' }));

    const dialog = await screen.findByTestId('nearby-contact-dialog');
    const nickname = within(dialog).getByRole('textbox', { name: 'Nickname' });
    expect(nickname).toHaveValue('Nearby Alice');
    await user.clear(nickname);
    await user.type(nickname, 'Alice');
    await user.click(within(dialog).getByTestId('nearby-contact-add-submit'));

    await waitFor(() => expect(identityAPI.addContactFromDiscovery).toHaveBeenCalledWith({
      nickname: 'Alice',
      peerId: 'peer-1',
    }));
    expect(screen.queryByTestId('nearby-contact-dialog')).not.toBeInTheDocument();
    await user.click(screen.getByText('All Contacts'));
    expect(await screen.findByText('Alice')).toBeInTheDocument();
  });

  it('shows a stable error when invite creation returns a malformed payload', async () => {
    identityAPI.createInvite.mockResolvedValue({ data: null });

    renderContacts();

    fireEvent.click(await screen.findByText('Create Invite'));

    expect(
      await screen.findByText(
        'Failed to create invite',
      ),
    ).toBeInTheDocument();
    expect(QRCode.toDataURL).not.toHaveBeenCalled();
  });

  it('renders structured add-contact errors as text', async () => {
    identityAPI.addContactFromInvite.mockRejectedValue({
      response: {
        data: {
          detail: 'Invite expired',
          status: 400,
          title: 'Bad Request',
        },
      },
    });

    renderContacts();

    fireEvent.click(await screen.findByText('Add Friend'));
    fireEvent.change(screen.getByTestId('contacts-add-invite-input'), {
      target: { value: 'slskdn://invite/expired' },
    });
    fireEvent.change(screen.getByTestId('contacts-contact-nickname'), {
      target: { value: 'Alice' },
    });
    fireEvent.click(screen.getByTestId('contacts-add-invite-submit'));

    expect(await screen.findByText('Failed to add contact')).toBeInTheDocument();
  });

  it('fills the invite input from a scanned QR image', async () => {
    const close = vi.fn();
    const detect = vi.fn().mockResolvedValue([
      {
        rawValue: 'slskdn://invite/scanned',
      },
    ]);

    window.BarcodeDetector = vi.fn(function BarcodeDetector() {
      return { detect };
    });
    window.createImageBitmap = vi.fn().mockResolvedValue({ close });

    renderContacts();

    fireEvent.click(await screen.findByText('Add Friend'));
    fireEvent.change(screen.getByTestId('contacts-add-invite-qr-file'), {
      target: {
        files: [new File(['qr'], 'invite.png', { type: 'image/png' })],
      },
    });

    await waitFor(() => {
      expect(screen.getByTestId('contacts-add-invite-input')).toHaveValue(
        'slskdn://invite/scanned',
      );
    });

    expect(window.BarcodeDetector).toHaveBeenCalledWith({ formats: ['qr_code'] });
    expect(detect).toHaveBeenCalled();
    expect(close).toHaveBeenCalled();
  });

  it('explains contact creation and discovery actions without activating them on hover', async () => {
    const user = userEvent.setup();
    const inviteTooltip = 'Generate a 24-hour invite link and QR code so a friend can add you.';
    const nearbyTooltip = 'Query local-network discovery again to refresh the nearby peers list.';
    renderContacts();

    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: 'Create Invite' })).toHaveLength(2);
    });
    for (const button of screen.getAllByRole('button', { name: 'Create Invite' })) {
      await user.hover(button);
      expect(await screen.findByText(inviteTooltip)).toBeInTheDocument();
      await user.unhover(button);
    }
    expect(identityAPI.createInvite).not.toHaveBeenCalled();

    const addFriend = screen.getByRole('button', { name: 'Add Friend' });
    await user.hover(addFriend);
    expect(await screen.findByText(
      'Open the form to add a contact from an invite link or QR code.',
    )).toBeInTheDocument();
    expect(screen.queryByTestId('contacts-add-invite-input')).not.toBeInTheDocument();

    await waitFor(() => expect(identityAPI.getNearby).toHaveBeenCalledTimes(1));
    await user.hover(screen.getByRole('button', { name: 'Refresh Nearby' }));
    expect(await screen.findByText(nearbyTooltip)).toBeInTheDocument();
    expect(identityAPI.getNearby).toHaveBeenCalledTimes(1);
  });

  it('explains invite modal actions without submitting or closing on hover', async () => {
    const user = userEvent.setup();
    renderContacts();

    await user.click(await screen.findByRole('button', { name: 'Create Invite' }));
    expect(await screen.findByTestId('contacts-invite-output')).toHaveValue(
      'slskdn://invite/test-invite',
    );

    const close = screen.getByRole('button', { name: 'Close' });
    await user.hover(close);
    expect(await screen.findByText('Close the invite and return to your contacts list.'))
      .toBeInTheDocument();
    expect(screen.getByTestId('contacts-invite-output')).toBeInTheDocument();

    await user.click(close);
    await user.click(screen.getByRole('button', { name: 'Add Friend' }));
    const submit = screen.getByRole('button', { name: 'Add Contact' });
    await user.hover(submit);
    expect(await screen.findByText('Validate the invite link and save this peer to your contacts.'))
      .toBeInTheDocument();
    expect(identityAPI.addContactFromInvite).not.toHaveBeenCalled();
  });

  it('names contact icon actions for assistive technology', async () => {
    const user = userEvent.setup();
    identityAPI.getContacts.mockResolvedValue({
      data: [{ id: 'contact-1', nickname: 'Alice', peerId: 'alice-peer' }],
    });
    renderContacts();

    const chat = await screen.findByRole('button', { name: 'Chat with Alice' });
    expect(screen.getByRole('button', { name: 'Browse files shared by Alice' }))
      .toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Remove Alice as a contact' }))
      .toBeInTheDocument();

    await user.hover(chat);
    expect(await screen.findByText('Open a private chat with this contact.'))
      .toBeInTheDocument();
  });
});
