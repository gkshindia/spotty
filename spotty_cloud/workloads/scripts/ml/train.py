#!/usr/bin/env python
# Basic deep learning training script for Spotty

import os
import tensorflow as tf
import numpy as np
import argparse
from datetime import datetime

# Parse command line arguments
def parse_args():
    parser = argparse.ArgumentParser(description='Train a basic neural network model')
    parser.add_argument('--epochs', type=int, default=10, help='Number of epochs')
    parser.add_argument('--batch_size', type=int, default=32, help='Batch size')
    parser.add_argument('--lr', type=float, default=0.001, help='Learning rate')
    parser.add_argument('--save_dir', type=str, default='./models', help='Directory to save models')
    return parser.parse_args()

# Main training function
def train(args):
    print(f"TensorFlow version: {tf.__version__}")
    print(f"Training with: epochs={args.epochs}, batch_size={args.batch_size}, lr={args.lr}")
    
    # Create model save directory if it doesn't exist
    os.makedirs(args.save_dir, exist_ok=True)
    
    # Load MNIST dataset for demonstration
    mnist = tf.keras.datasets.mnist
    (x_train, y_train), (x_test, y_test) = mnist.load_data()
    x_train, x_test = x_train / 255.0, x_test / 255.0
    
    # Define a simple model
    model = tf.keras.models.Sequential([
        tf.keras.layers.Flatten(input_shape=(28, 28)),
        tf.keras.layers.Dense(128, activation='relu'),
        tf.keras.layers.Dropout(0.2),
        tf.keras.layers.Dense(10, activation='softmax')
    ])
    
    # Compile the model
    model.compile(
        optimizer=tf.keras.optimizers.legacy.Adam(learning_rate=args.lr),
        loss='sparse_categorical_crossentropy',
        metrics=['accuracy']
    )
    
    # Set up TensorBoard logging
    log_dir = os.path.join('logs', datetime.now().strftime("%Y%m%d-%H%M%S"))
    tensorboard_callback = tf.keras.callbacks.TensorBoard(
        log_dir=log_dir, histogram_freq=1, write_graph=True
    )
    
    # Train the model
    model.fit(
        x_train, y_train,
        epochs=args.epochs,
        batch_size=args.batch_size,
        validation_data=(x_test, y_test),
        callbacks=[tensorboard_callback]
    )
    
    # Evaluate the model
    test_loss, test_acc = model.evaluate(x_test, y_test, verbose=2)
    print(f"\nTest accuracy: {test_acc:.4f}")
    
    # Save the model
    model_path = os.path.join(args.save_dir, 'mnist_model')
    model.save(model_path)
    print(f"Model saved to {model_path}")

if __name__ == '__main__':
    args = parse_args()
    train(args)
