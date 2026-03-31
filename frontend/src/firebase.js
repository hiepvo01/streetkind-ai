import { initializeApp } from 'firebase/app';
import { getAuth } from 'firebase/auth';
import { getDatabase } from 'firebase/database';

const firebaseConfig = {
  apiKey: "AIzaSyD6q7A5-g26ma7Dv2w8PLa4e0FdM_D3eVQ",
  authDomain: "streetkind-app-dev.firebaseapp.com",
  databaseURL: "https://streetkind-app-dev-default-rtdb.firebaseio.com",
  projectId: "streetkind-app-dev",
  storageBucket: "streetkind-app-dev.firebasestorage.app",
  messagingSenderId: "1092518570833",
  appId: "1:1092518570833:web:78d7d10ed2810027a68170",
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const database = getDatabase(app);
