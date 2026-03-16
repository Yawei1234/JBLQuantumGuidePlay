// import { ChildHandshake, WorkerMessenger } from 'post-me';
self.importScripts('postme.js');

// const { ChildHandshake, WorkerMessenger } = postme;

// Methods exposed by the worker: each function can either return a value or a Promise.
const methods = {
  sum: (x, y) => x + y,
  mul: (x, y) => x * y
}

const messenger = WorkerMessenger({worker: self});
ChildHandshake(messenger, methods).then((connection) => {
  const localHandle = connection.localHandle();

  // Emit custom events to the app
  localHandle.emit('ping',  'Oh, hi!');
});